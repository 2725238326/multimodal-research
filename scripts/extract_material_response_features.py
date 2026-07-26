import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np


KNOWN_WORKSPACE_MARKERS = ("data/", "experiments/", "models/")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, default=Path("."))
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-samples", type=int)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path):
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            required = {
                "sample_id",
                "region_id",
                "scene",
                "light_dir",
                "material_label",
                "rgb_crop_path",
                "albedo_crop_path",
            }
            missing = sorted(required - row.keys())
            if missing:
                raise ValueError(f"{path}:{line_number} missing {missing}")
            rows.append(row)
    return rows


def resolve_repo_path(value, workspace_root):
    normalized = str(value).replace("\\", "/")
    for marker in KNOWN_WORKSPACE_MARKERS:
        position = normalized.find(marker)
        if position >= 0:
            return (workspace_root / normalized[position:]).resolve()
    path = Path(value)
    return path.resolve() if path.is_absolute() else (workspace_root / path).resolve()


def validate_rows(rows, workspace_root):
    sample_ids = set()
    missing = []
    for row in rows:
        sample_id = row["sample_id"]
        if sample_id in sample_ids:
            raise ValueError(f"duplicate sample_id: {sample_id}")
        sample_ids.add(sample_id)
        for key in ("rgb_crop_path", "albedo_crop_path"):
            path = resolve_repo_path(row[key], workspace_root)
            if not path.is_file():
                missing.append({"sample_id": sample_id, "key": key, "path": str(path)})
    return missing


def feature_tensor(output):
    import torch

    if torch.is_tensor(output):
        return output
    for attribute in ("image_embeds", "pooler_output"):
        value = getattr(output, attribute, None)
        if torch.is_tensor(value):
            return value
    last_hidden_state = getattr(output, "last_hidden_state", None)
    if torch.is_tensor(last_hidden_state):
        return last_hidden_state.mean(dim=1)
    raise TypeError(f"unsupported image feature output: {type(output).__name__}")


def encode_images(paths, model, processor, device, batch_size):
    import torch
    from PIL import Image

    outputs = []
    for start in range(0, len(paths), batch_size):
        batch_paths = paths[start : start + batch_size]
        images = []
        for path in batch_paths:
            with Image.open(path) as image:
                images.append(image.convert("RGB"))
        inputs = processor(images=images, return_tensors="pt")
        pixel_values = inputs["pixel_values"].to(device)
        with torch.inference_mode():
            if device.startswith("cuda"):
                with torch.autocast(device_type="cuda", dtype=torch.float16):
                    features = feature_tensor(
                        model.get_image_features(pixel_values=pixel_values)
                    )
            else:
                features = feature_tensor(
                    model.get_image_features(pixel_values=pixel_values)
                )
        features = torch.nn.functional.normalize(features.float(), dim=-1)
        outputs.append(features.cpu().numpy())
    return np.concatenate(outputs, axis=0).astype(np.float32)


def main():
    args = parse_args()
    started = time.time()
    workspace_root = args.workspace_root.resolve()
    rows = load_jsonl(args.manifest)
    if args.max_samples is not None:
        rows = rows[: args.max_samples]
    missing = validate_rows(rows, workspace_root)
    dry_summary = {
        "status": "blocked" if missing else "smoke_test",
        "dry_run": args.dry_run,
        "manifest": str(args.manifest),
        "manifest_sha256": sha256(args.manifest),
        "sample_count": len(rows),
        "region_count": len({row["region_id"] for row in rows}),
        "scene_count": len({row["scene"] for row in rows}),
        "material_count": len({row["material_label"] for row in rows}),
        "missing_file_count": len(missing),
        "missing_files": missing[:20],
        "model_dir": str(args.model_dir),
        "model_revision": args.model_revision,
        "device": args.device,
        "batch_size": args.batch_size,
    }
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    if missing or args.dry_run:
        args.summary_output.write_text(
            json.dumps(dry_summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(dry_summary, ensure_ascii=False, indent=2))
        if missing:
            raise SystemExit(2)
        return

    import torch
    from transformers import AutoModel, AutoProcessor

    if not args.model_dir.is_dir():
        raise FileNotFoundError(args.model_dir)
    if args.device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA device requested but torch.cuda.is_available() is false")
    processor = AutoProcessor.from_pretrained(args.model_dir, local_files_only=True)
    model = AutoModel.from_pretrained(args.model_dir, local_files_only=True)
    model = model.eval().to(args.device)
    rgb_paths = [resolve_repo_path(row["rgb_crop_path"], workspace_root) for row in rows]
    albedo_paths = [
        resolve_repo_path(row["albedo_crop_path"], workspace_root) for row in rows
    ]
    rgb_features = encode_images(
        rgb_paths, model, processor, args.device, args.batch_size
    )
    albedo_features = encode_images(
        albedo_paths, model, processor, args.device, args.batch_size
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output,
        sample_ids=np.asarray([row["sample_id"] for row in rows]),
        region_ids=np.asarray([row["region_id"] for row in rows]),
        scenes=np.asarray([row["scene"] for row in rows]),
        labels=np.asarray([row["material_label"] for row in rows]),
        light_dirs=np.asarray([int(row["light_dir"]) for row in rows], dtype=np.int16),
        rgb_features=rgb_features,
        albedo_features=albedo_features,
    )
    summary = {
        **dry_summary,
        "status": "completed",
        "dry_run": False,
        "feature_dimension": int(rgb_features.shape[1]),
        "feature_cache": str(args.output),
        "feature_cache_sha256": sha256(args.output),
        "elapsed_seconds": round(time.time() - started, 3),
        "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda,
        "gpu_name": torch.cuda.get_device_name(args.device)
        if args.device.startswith("cuda")
        else None,
    }
    args.summary_output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
