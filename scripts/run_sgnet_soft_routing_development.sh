#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 9 ]]; then
  echo "Usage: $0 WORKER_INDEX WORKER_COUNT PHYSICAL_GPU EXPERIMENT_ROOT SGNET_DIR DATA_ROOT PYTHON GATE_REFERENCE_MEAN DROP_THRESHOLD"
  exit 2
fi

worker_index=$1
worker_count=$2
physical_gpu=$3
experiment_root=$4
sgnet_dir=$5
data_root=$6
python_bin=$7
gate_reference_mean=$8
drop_threshold=$9

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
output_root="${experiment_root}/relative_soft_routing/development_seed_20260723"
base_checkpoint="${sgnet_dir}/cpts/SGNet_X16_R.pth"
gate_checkpoint="${experiment_root}/reliability_gate_full_nyu_seed_20260723/sgnet_reliability_gate.pth"
temperatures=(0.005 0.01 0.02)
conditions=(clean checker8)
mkdir -p "${output_root}/logs"

job_index=0
for temperature in "${temperatures[@]}"; do
  for condition in "${conditions[@]}"; do
    if (( job_index % worker_count == worker_index )); then
      texture_args=()
      if [[ "${condition}" == "checker8" ]]; then
        texture_args=(--texture-pattern checkerboard --texture-amplitude 8)
      fi
      log_path="${output_root}/logs/temperature_${temperature}_${condition}.log"
      CUDA_VISIBLE_DEVICES="${physical_gpu}" "${python_bin}" \
        "${script_dir}/evaluate_sgnet_reliability_gate_rgbdd_x16.py" \
        --sgnet-dir "${sgnet_dir}" \
        --data-root "${data_root}" \
        --checkpoint "${base_checkpoint}" \
        --gate-checkpoint "${gate_checkpoint}" \
        --output-dir "${output_root}/temperature_${temperature}/${condition}" \
        --device cuda:0 \
        --gate-application soft_adaptive \
        --gate-reference-mean "${gate_reference_mean}" \
        --reference-drop-threshold "${drop_threshold}" \
        --adaptive-temperature "${temperature}" \
        --max-samples 100 \
        "${texture_args[@]}" >"${log_path}" 2>&1
    fi
    ((job_index += 1))
  done
done
