#!/bin/bash
set -e

MODEL_DIR="${MODEL_DIR:-/models}"
MODEL_NAME="${MODEL_NAME:-glm-asr}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-9930}"
HF_MODEL_ID="${HF_MODEL_ID:-zai-org/GLM-ASR-Nano-2512}"
MS_MODEL_ID="${MS_MODEL_ID:-ZhipuAI/GLM-ASR-Nano-2512}"
MODEL_SOURCE="${MODEL_SOURCE:-huggingface}"

if [ -n "${HF_ENDPOINT}" ]; then
    export HF_ENDPOINT
fi

if [ "$MODEL_SOURCE" = "modelscope" ]; then
    LOCAL_MODEL_PATH="${MODEL_DIR}/${MS_MODEL_ID}"
    if [ ! -d "${LOCAL_MODEL_PATH}" ] || [ -z "$(ls -A "${LOCAL_MODEL_PATH}" 2>/dev/null)" ]; then
        python3 -c "
from modelscope import snapshot_download
snapshot_download('${MS_MODEL_ID}', local_dir='${LOCAL_MODEL_PATH}')
print('Model downloaded from ModelScope to ${LOCAL_MODEL_PATH}')
"
    else
        echo "Model already exists at ${LOCAL_MODEL_PATH}, skipping download."
    fi
else
    LOCAL_MODEL_PATH="${MODEL_DIR}/${HF_MODEL_ID}"
    if [ ! -d "${LOCAL_MODEL_PATH}" ] || [ -z "$(ls -A "${LOCAL_MODEL_PATH}" 2>/dev/null)" ]; then
        hf download "${HF_MODEL_ID}" --local-dir "${LOCAL_MODEL_PATH}"
    else
        echo "Model already exists at ${LOCAL_MODEL_PATH}, skipping download."
    fi
fi

echo "Starting GLM-ASR server with model from: ${LOCAL_MODEL_PATH}"
exec python3 /app/server.py \
    --model-path "${LOCAL_MODEL_PATH}" \
    --served-model-name "${MODEL_NAME}" \
    --host "${HOST}" \
    --port "${PORT}"
