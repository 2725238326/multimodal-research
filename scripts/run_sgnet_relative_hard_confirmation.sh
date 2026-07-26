#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 8 ]]; then
  echo "Usage: $0 WORKER_INDEX WORKER_COUNT PHYSICAL_GPU EXPERIMENT_ROOT SGNET_DIR DATA_ROOT PYTHON DROP_THRESHOLD"
  exit 2
fi

worker_index=$1
worker_count=$2
physical_gpu=$3
experiment_root=$4
sgnet_dir=$5
data_root=$6
python_bin=$7
drop_threshold=$8

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
output_root="${experiment_root}/relative_hard_confirmation"
base_checkpoint="${sgnet_dir}/cpts/SGNet_X16_R.pth"
seeds=(20260724 20260725)
conditions=(clean checker8 sinusoidal8 noise8)
declare -A reference_means
reference_means[20260724]=0.7797970684958093
reference_means[20260725]=0.800801091282456
mkdir -p "${output_root}/logs"

job_index=0
for seed in "${seeds[@]}"; do
  gate_checkpoint="${experiment_root}/reliability_gate_full_nyu_seed_${seed}/sgnet_reliability_gate.pth"
  for condition in "${conditions[@]}"; do
    if (( job_index % worker_count == worker_index )); then
      texture_args=()
      case "${condition}" in
        checker8)
          texture_args=(--texture-pattern checkerboard --texture-amplitude 8)
          ;;
        sinusoidal8)
          texture_args=(--texture-pattern sinusoidal --texture-amplitude 8 --texture-period 8)
          ;;
        noise8)
          texture_args=(--texture-pattern noise --texture-amplitude 8 --texture-seed 20260723)
          ;;
      esac
      log_path="${output_root}/logs/seed_${seed}_${condition}.log"
      CUDA_VISIBLE_DEVICES="${physical_gpu}" "${python_bin}" \
        "${script_dir}/evaluate_sgnet_reliability_gate_rgbdd_x16.py" \
        --sgnet-dir "${sgnet_dir}" \
        --data-root "${data_root}" \
        --checkpoint "${base_checkpoint}" \
        --gate-checkpoint "${gate_checkpoint}" \
        --output-dir "${output_root}/seed_${seed}/${condition}" \
        --device cuda:0 \
        --gate-application adaptive \
        --gate-reference-mean "${reference_means[${seed}]}" \
        --reference-drop-threshold "${drop_threshold}" \
        "${texture_args[@]}" >"${log_path}" 2>&1
    fi
    ((job_index += 1))
  done
done
