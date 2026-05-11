#!/bin/bash
# Start Qwen2.5-VL-7B-AWQ via vLLM on port 8001.
# --gpu-memory-utilization 0.45 leaves ~55% VRAM for Qwen3-8B on the same GPU.

set -euo pipefail

MODEL="Qwen/Qwen2.5-VL-7B-Instruct-AWQ"
PORT=8001
API_KEY="${VLLM_API_KEY:-token-abc}"

echo "Starting ${MODEL} on port ${PORT}..."

vllm serve "${MODEL}" \
    --port "${PORT}" \
    --api-key "${API_KEY}" \
    --gpu-memory-utilization 0.45 \
    --max-model-len 8192 \
    --dtype half \
    --enable-auto-tool-choice \
    --tool-call-parser hermes \
    --trust-remote-code
