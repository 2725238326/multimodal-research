#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 7 ]]; then
  echo "Usage: $0 WORKER_INDEX WORKER_COUNT PHYSICAL_GPU EXPERIMENT_ROOT SGNET_DIR DATA_ROOT PYTHON"
  exit 2
fi

worker_index=$1
worker_count=$2
physical_gpu=$3
experiment_root=$4
sgnet_dir=$5
data_root=$6
python_bin=$7

if (( worker_index < 0 || worker_index >= worker_count )); then
  echo "WORKER_INDEX must satisfy 0 <= index < WORKER_COUNT"
  exit 2
fi

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
output_root="${experiment_root}/unseen_texture_generalization"
base_checkpoint="${sgnet_dir}/cpts/SGNet_X16_R.pth"
texture_seed=20260723
texture_period=8
adaptive_threshold=0.75
gate_seeds=(20260723 20260724 20260725)
patterns=(sinusoidal noise)
amplitudes=(8 16)

mkdir -p "${output_root}/logs"

run_job() {
  local job_index=$1
  shift
  if (( job_index % worker_count != worker_index )); then
    return
  fi
  echo "[$(date --iso-8601=seconds)] worker=${worker_index} job=${job_index} command=$*"
  CUDA_VISIBLE_DEVICES="${physical_gpu}" "$@"
}

job_index=0
for pattern in "${patterns[@]}"; do
  for amplitude in "${amplitudes[@]}"; do
    condition="${pattern}_amp_${amplitude}"
    pattern_args=(--texture-pattern "${pattern}" --texture-amplitude "${amplitude}")
    if [[ "${pattern}" == "sinusoidal" ]]; then
      pattern_args+=(--texture-period "${texture_period}")
    else
      pattern_args+=(--texture-seed "${texture_seed}")
    fi
    run_job "${job_index}" \
      "${python_bin}" "${script_dir}/evaluate_sgnet_rgbdd_x16.py" \
      --sgnet-dir "${sgnet_dir}" \
      --data-root "${data_root}" \
      --checkpoint "${base_checkpoint}" \
      --output-dir "${output_root}/baseline/${condition}" \
      --device cuda:0 \
      "${pattern_args[@]}" \
      >"${output_root}/logs/baseline_${condition}.log" 2>&1
    ((job_index += 1))
  done
done

for gate_seed in "${gate_seeds[@]}"; do
  gate_checkpoint="${experiment_root}/reliability_gate_full_nyu_seed_${gate_seed}/sgnet_reliability_gate.pth"
  for pattern in "${patterns[@]}"; do
    for amplitude in "${amplitudes[@]}"; do
      condition="${pattern}_amp_${amplitude}"
      pattern_args=(--texture-pattern "${pattern}" --texture-amplitude "${amplitude}")
      if [[ "${pattern}" == "sinusoidal" ]]; then
        pattern_args+=(--texture-period "${texture_period}")
      else
        pattern_args+=(--texture-seed "${texture_seed}")
      fi
      run_job "${job_index}" \
        "${python_bin}" "${script_dir}/evaluate_sgnet_reliability_gate_rgbdd_x16.py" \
        --sgnet-dir "${sgnet_dir}" \
        --data-root "${data_root}" \
        --checkpoint "${base_checkpoint}" \
        --gate-checkpoint "${gate_checkpoint}" \
        --output-dir "${output_root}/adaptive_seed_${gate_seed}/${condition}" \
        --device cuda:0 \
        --gate-application adaptive \
        --adaptive-threshold "${adaptive_threshold}" \
        "${pattern_args[@]}" \
        >"${output_root}/logs/adaptive_seed_${gate_seed}_${condition}.log" 2>&1
      ((job_index += 1))
    done
  done
done

echo "[$(date --iso-8601=seconds)] worker=${worker_index} completed"
