import argparse
import base64
import io
import tempfile
import time
import uuid
from pathlib import Path

import numpy as np
import requests as req_lib
import soundfile as sf
import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoModel, AutoProcessor
from typing import Optional


def save_audio_to_temp(audio_input: str) -> str:
    if audio_input.startswith("data:"):
        parts = audio_input.split(",", 1)
        if len(parts) != 2:
            raise ValueError("Invalid data URI format")
        audio_bytes = base64.b64decode(parts[1])
        suffix = ".wav"
        if "audio/mp4" in parts[0]:
            suffix = ".mp4"
        elif "audio/mpeg" in parts[0]:
            suffix = ".mp3"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_bytes)
            return f.name
    elif audio_input.startswith(("http://", "https://")):
        resp = req_lib.get(audio_input, timeout=60)
        resp.raise_for_status()
        suffix = ".wav"
        ct = resp.headers.get("content-type", "")
        if "mp4" in ct:
            suffix = ".mp4"
        elif "mpeg" in ct:
            suffix = ".mp3"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(resp.content)
            return f.name
    else:
        path = audio_input
        if path.startswith("file://"):
            path = path[7:]
        return path


class ASRModel:
    def __init__(self, model_path: str, device: str = "cuda"):
        self.device = device
        print(f"Loading model from {model_path}...")

        self.processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
        self.model = AutoModel.from_pretrained(
            model_path,
            dtype=torch.bfloat16,
            trust_remote_code=True,
        ).to(device)
        self.model.eval()
        print("Model loaded successfully.")

    @torch.inference_mode()
    def transcribe(self, audio_path: str, text_prompt: str, max_new_tokens: int = 128) -> str:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "audio", "url": audio_path},
                    {"type": "text", "text": text_prompt},
                ],
            }
        ]

        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        )
        inputs = inputs.to(self.device, dtype=torch.bfloat16)

        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
        )
        prompt_len = inputs["input_ids"].shape[1]
        transcript_ids = outputs[0, prompt_len:].cpu().tolist()
        transcript = self.processor.tokenizer.decode(transcript_ids, skip_special_tokens=True).strip()
        return transcript


app = FastAPI(title="GLM-ASR OpenAI-Compatible API")
asr_model: Optional[ASRModel] = None
served_model_name = "glm-asr"


class ChatMessage(BaseModel):
    role: str
    content: str | list


class ChatCompletionRequest(BaseModel):
    model: str = "glm-asr"
    messages: list[ChatMessage]
    max_tokens: int = 1024
    temperature: float = 0.0
    stream: bool = False


class ModelObject(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "glm-asr"


class ModelListResponse(BaseModel):
    object: str = "list"
    data: list[ModelObject]


class ChatChoice(BaseModel):
    index: int
    message: dict
    finish_reason: str


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatChoice]
    usage: UsageInfo


@app.get("/v1/models")
async def list_models():
    return ModelListResponse(
        data=[
            ModelObject(
                id=served_model_name,
                created=int(time.time()),
                owned_by="glm-asr",
            )
        ]
    )


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    if asr_model is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")

    audio_url = None
    text_prompt = "Please transcribe this audio into text"

    for msg in request.messages:
        if isinstance(msg.content, list):
            for item in msg.content:
                if isinstance(item, dict):
                    if item.get("type") == "audio_url":
                        audio_url = item["audio_url"]["url"]
                    elif item.get("type") == "text":
                        text_prompt = item["text"]
        elif isinstance(msg.content, str) and msg.role == "user":
            text_prompt = msg.content

    if audio_url is None:
        raise HTTPException(
            status_code=400,
            detail="No audio_url provided. This API only supports audio transcription.",
        )

    temp_path = None
    try:
        temp_path = save_audio_to_temp(audio_url)
        transcript = asr_model.transcribe(temp_path, text_prompt, max_new_tokens=request.max_tokens)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_path and (audio_url.startswith("data:") or audio_url.startswith(("http://", "https://"))):
            Path(temp_path).unlink(missing_ok=True)

    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
        created=int(time.time()),
        model=request.model,
        choices=[
            ChatChoice(
                index=0,
                message={"role": "assistant", "content": transcript},
                finish_reason="stop",
            )
        ],
        usage=UsageInfo(
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
        ),
    )


@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": asr_model is not None}


def main():
    parser = argparse.ArgumentParser(description="GLM-ASR OpenAI-Compatible Server")
    parser.add_argument("--model-path", type=str, required=True)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9930)
    parser.add_argument("--served-model-name", type=str, default="glm-asr")
    parser.add_argument(
        "--device",
        type=str,
        default="cuda" if torch.cuda.is_available() else "cpu",
    )
    args = parser.parse_args()

    global served_model_name
    served_model_name = args.served_model_name

    global asr_model
    asr_model = ASRModel(args.model_path, args.device)

    print(f"Starting server on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
