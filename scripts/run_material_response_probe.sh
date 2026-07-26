#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "usage: $0 WORKSPACE_ROOT MODEL_DIR OUTPUT_ROOT [DEVICE] [full|smoke]" >&2
  exit 2
fi

workspace_root=$1
model_dir=$2
output_root=$3
device=${4:-cuda:0}
mode=${5:-full}

if [[ "$mode" == "smoke" ]]; then
  manifest="$workspace_root/experiments/manifests/material_response_probe_v0/material_response_probe_smoke.jsonl"
elif [[ "$mode" == "full" ]]; then
  manifest="$workspace_root/experiments/manifests/material_constancy_albedo_v1/material_constancy_albedo_manifest.jsonl"
else
  echo "mode must be full or smoke" >&2
  exit 2
fi
config="$workspace_root/configs/material_response_probe_v0.json"
feature_cache="$output_root/features/siglip2_features.npz"
extract_summary="$output_root/aggregate/extract_summary.json"
result_summary="$output_root/aggregate/result_summary.json"
predictions="$output_root/local_only/predictions.jsonl"

mkdir -p "$output_root/features" "$output_root/aggregate" "$output_root/local_only"

extract_args=(
  python "$workspace_root/scripts/extract_material_response_features.py"
  --manifest "$manifest"
  --workspace-root "$workspace_root"
  --model-dir "$model_dir"
  --model-revision 75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2
  --output "$feature_cache"
  --summary-output "$extract_summary"
  --device "$device"
  --batch-size 8
)
"${extract_args[@]}"

evaluate_args=(
  python "$workspace_root/scripts/evaluate_material_response_probe.py"
  --features "$feature_cache"
  --config "$config"
  --output "$result_summary"
  --predictions-output "$predictions"
)
if [[ "$mode" == "smoke" ]]; then
  evaluate_args+=(--bootstrap-draws 200)
fi
"${evaluate_args[@]}"
