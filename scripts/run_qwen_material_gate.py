#!/usr/bin/env python3
"""Run deterministic Qwen3-VL material classification on an RGB-only manifest."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration


ALIASES = {
    "fabric/cloth": ["fabric", "cloth", "textile"],
    "granite/marble": ["granite", "marble"],
    "paper/tissue": ["paper", "tissue"],
    "clear plastic": ["clear plastic", "transparent plastic"],
    "opaque plastic": ["opaque plastic", "plastic"],
    "carpet/rug": ["carpet", "rug"],
}


def parse_label(text: str, candidates: list[str]) -> str | None:
    normalized = re.sub(r"[^a-z/ ]+", " ", text.lower()).strip()
    for candidate in sorted(candidates, key=len, reverse=True):
        if normalized == candidate:
            return candidate
    for candidate in sorted(candidates, key=len, reverse=True):
        terms = [candidate, *ALIASES.get(candidate, [])]
        if any(re.search(rf"\b{re.escape(term)}\b", normalized) for term in terms):
            return candidate
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-new-tokens", type=int, default=24)
    parser.add_argument("--image-key", default="crop_path")
    parser.add_argument("--secondary-image-key")
    parser.add_argument("--condition-name", default="rgb")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--evidence-key")
    parser.add_argument("--prompt-prefix")
    args = parser.parse_args()

    samples = [json.loads(line) for line in args.manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.limit is not None:
        samples = samples[: args.limit]
    completed = {}
    if args.output.exists():
        for line in args.output.read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line)
                completed[item["sample_id"]] = item

    processor = AutoProcessor.from_pretrained(str(args.model), local_files_only=True)
    torch_dtype = (
        torch.bfloat16
        if torch.cuda.get_device_capability(0)[0] >= 8
        else torch.float16
    )
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        str(args.model),
        local_files_only=True,
        torch_dtype=torch_dtype,
        device_map={"": 0},
        attn_implementation="sdpa",
    ).eval()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("a", encoding="utf-8") as handle:
        for index, sample in enumerate(samples, start=1):
            if sample["sample_id"] in completed:
                continue
            labels = sample["candidate_labels"]
            paired = args.secondary_image_key is not None
            prefix = args.prompt_prefix or (
                "The first image is an RGB close-up and the second is its aligned estimated albedo. "
                "Classify the primary surface material in the close-up. "
                if paired
                else "Classify the primary surface material in this close-up image. "
            )
            prompt = prefix + "Choose exactly one label from: " + "; ".join(labels) + ". Answer with the label only."
            if args.evidence_key:
                prompt = sample[args.evidence_key] + " Treat it as noisy auxiliary evidence. " + prompt
            content = [{"type": "image", "image": Image.open(sample[args.image_key]).convert("RGB")}]
            if paired:
                content.append(
                    {"type": "image", "image": Image.open(sample[args.secondary_image_key]).convert("RGB")}
                )
            content.append({"type": "text", "text": prompt})
            messages = [{"role": "user", "content": content}]
            inputs = processor.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_dict=True,
                return_tensors="pt",
            ).to(model.device)
            started = time.time()
            with torch.inference_mode():
                output_ids = model.generate(
                    **inputs,
                    max_new_tokens=args.max_new_tokens,
                    do_sample=False,
                    use_cache=True,
                )
            trimmed = output_ids[:, inputs.input_ids.shape[1] :]
            raw = processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0].strip()
            predicted = parse_label(raw, labels)
            record = {
                **sample,
                "model": args.model.name,
                "torch_dtype": str(torch_dtype),
                "condition": args.condition_name,
                "image_key": args.image_key,
                "secondary_image_key": args.secondary_image_key,
                "evidence_key": args.evidence_key,
                "prompt": prompt,
                "raw_output": raw,
                "predicted_label": predicted,
                "correct": predicted == sample["material_label"],
                "latency_s": round(time.time() - started, 4),
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
            print(f"[{index}/{len(samples)}] {sample['sample_id']} gt={sample['material_label']} pred={predicted} raw={raw!r}", flush=True)


if __name__ == "__main__":
    main()
