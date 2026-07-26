import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np

try:
    from scripts.extract_material_response_features import encode_images, resolve_repo_path
except ModuleNotFoundError:
    from extract_material_response_features import encode_images, resolve_repo_path


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
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


def read_manifest(path):
    required = {
        "sample_id",
        "region_id",
        "scene",
        "light_dir",
        "material_label",
        "rgb_crop_path",
    }
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            missing = sorted(required - row.keys())
            if missing:
                raise ValueError(f"{path}:{line_number} missing {missing}")
            rows.append(row)
    return rows


def main():
    args = parse_args()
    started = time.time()
    workspace_root = args.workspace_root.resolve()
    rows = read_manifest(args.manifest)
    if args.max_samples:
        rows = rows[: args.max_samples]
    paths = [resolve_repo_path(row["rgb_crop_path"], workspace_root) for row in rows]
    missing = [str(path) for path in paths if not path.is_file()]
    if len({row["sample_id"] for row in rows}) != len(rows):
        raise ValueError("duplicate sample IDs")
    summary = {
        "status": "Blocked" if missing else "Smoke test",
        "dry_run": bool(args.dry_run),
        "manifest_sha256": sha256(args.manifest),
        "sample_count": len(rows),
        "region_count": len({row["region_id"] for row in rows}),
        "scene_count": len({row["scene"] for row in rows}),
        "class_count": len({row["material_label"] for row in rows}),
        "missing_file_count": len(missing),
        "model_revision": args.model_revision,
        "device": args.device,
    }
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    if missing:
        summary["missing_files"] = missing[:20]
        args.summary_output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        raise FileNotFoundError(missing[0])
    if args.dry_run:
        args.summary_output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return

    import torch
    from transformers import AutoModel, AutoProcessor

    if not args.model_dir.is_dir():
        raise FileNotFoundError(args.model_dir)
    if args.device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    processor = AutoProcessor.from_pretrained(args.model_dir, local_files_only=True)
    model = AutoModel.from_pretrained(args.model_dir, local_files_only=True).eval().to(args.device)
    features = encode_images(paths, model, processor, args.device, args.batch_size)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output,
        sample_ids=np.asarray([row["sample_id"] for row in rows]),
        region_ids=np.asarray([row["region_id"] for row in rows]),
        scenes=np.asarray([row["scene"] for row in rows]),
        labels=np.asarray([row["material_label"] for row in rows]),
        light_dirs=np.asarray([int(row["light_dir"]) for row in rows], dtype=np.int16),
        rgb_features=features,
    )
    summary.update(
        {
            "status": "Completed",
            "dry_run": False,
            "feature_dimension": int(features.shape[1]),
            "feature_cache_sha256": sha256(args.output),
            "elapsed_seconds": round(time.time() - started, 3),
            "torch_version": torch.__version__,
            "cuda_version": torch.version.cuda,
            "gpu_name": torch.cuda.get_device_name(args.device)
            if args.device.startswith("cuda")
            else None,
        }
    )
    args.summary_output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
