FROM nvidia/cuda:13.0.0-devel-ubuntu22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git python3 python3-pip python3-venv && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir \
    torch==2.9.1 torchaudio==2.9.1 \
    --index-url https://download.pytorch.org/whl/cu130 && \
    python3 -m pip install --no-cache-dir \
    "git+https://github.com/huggingface/transformers" \
    fastapi \
    python-multipart \
    uvicorn[standard] \
    modelscope \
    requests \
    soundfile \
    librosa

WORKDIR /app

COPY server.py /app/server.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
