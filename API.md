# OpenAI 兼容接口使用指南

## 概述

GLM-ASR 提供 OpenAI 兼容的 Chat Completions API，支持通过标准 HTTP 请求进行语音识别。

- **接口地址**：`http://<host>:9930/v1/chat/completions`
- **模型名称**：`glm-asr`
- **支持的音频输入方式**：base64 编码、HTTP/HTTPS URL

## 快速开始

### 1. Python（OpenAI SDK）

```bash
pip install openai
```

```python
from openai import OpenAI
import base64

client = OpenAI(api_key="EMPTY", base_url="http://localhost:9930/v1")

# 读取本地音频文件并编码为 base64
with open("audio.wav", "rb") as f:
    audio_b64 = base64.b64encode(f.read()).decode()

response = client.chat.completions.create(
    model="glm-asr",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "audio_url",
                    "audio_url": {"url": f"data:audio/wav;base64,{audio_b64}"}
                },
                {
                    "type": "text",
                    "text": "Please transcribe this audio into text"
                }
            ]
        }
    ],
    max_tokens=1024
)

print(response.choices[0].message.content)
```

### 2. Python（标准库，无第三方依赖）

```python
import json
import urllib.request
import base64

with open("audio.wav", "rb") as f:
    audio_b64 = base64.b64encode(f.read()).decode()

data = {
    "model": "glm-asr",
    "messages": [{
        "role": "user",
        "content": [
            {"type": "audio_url", "audio_url": {"url": f"data:audio/wav;base64,{audio_b64}"}},
            {"type": "text", "text": "Please transcribe this audio into text"}
        ]
    }],
    "max_tokens": 1024
}

req = urllib.request.Request(
    "http://localhost:9930/v1/chat/completions",
    data=json.dumps(data).encode(),
    headers={"Content-Type": "application/json"}
)
resp = urllib.request.urlopen(req, timeout=120)
result = json.loads(resp.read())
print(result["choices"][0]["message"]["content"])
```

### 3. curl

```bash
# 使用 base64 编码
AUDIO_B64=$(base64 -w0 audio.wav)
curl http://localhost:9930/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"glm-asr\",
    \"messages\": [{
      \"role\": \"user\",
      \"content\": [
        {\"type\": \"audio_url\", \"audio_url\": {\"url\": \"data:audio/wav;base64,${AUDIO_B64}\"}},
        {\"type\": \"text\", \"text\": \"Please transcribe this audio into text\"}
      ]
    }],
    \"max_tokens\": 1024
  }"

# 使用 URL
curl http://localhost:9930/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-asr",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "audio_url", "audio_url": {"url": "https://example.com/audio.wav"}},
        {"type": "text", "text": "Please transcribe this audio into text"}
      ]
    }],
    "max_tokens": 1024
  }'
```

## 请求格式

### POST `/v1/chat/completions`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 固定为 `glm-asr` |
| `messages` | array | 是 | 消息列表，包含音频和文本内容 |
| `max_tokens` | integer | 否 | 最大生成 token 数，默认 1024 |
| `temperature` | float | 否 | 保留参数，当前固定为 0 |
| `stream` | boolean | 否 | 保留参数，当前不支持流式输出 |

### messages 格式

```json
{
  "role": "user",
  "content": [
    {
      "type": "audio_url",
      "audio_url": {
        "url": "<音频地址>"
      }
    },
    {
      "type": "text",
      "text": "<提示文本>"
    }
  ]
}
```

### 音频地址格式

| 格式 | 示例 |
|------|------|
| Base64 | `data:audio/wav;base64,UklGRi...` |
| HTTP URL | `https://example.com/audio.wav` |
| HTTPS URL | `https://example.com/audio.mp3` |

### 支持的音频格式

WAV、MP3、MP4、FLAC、OGG 等常见格式。

### 提示文本

`text` 字段用于指定识别指令，支持多语言：

| 语言 | 提示文本 |
|------|----------|
| 英文 | `Please transcribe this audio into text` |
| 中文 | `请将这段音频转录为文字` |
| 通用 | `Transcribe this audio` |

## 响应格式

```json
{
  "id": "chatcmpl-xxxxxxxxxxxxxxxxxxxxxxxx",
  "object": "chat.completion",
  "created": 1779284806,
  "model": "glm-asr",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "转录文本内容"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0
  }
}
```

## 辅助接口

### GET `/v1/models`

返回可用模型列表。

```bash
curl http://localhost:9930/v1/models
```

响应：

```json
{
  "object": "list",
  "data": [
    {
      "id": "glm-asr",
      "object": "model",
      "created": 1779284806,
      "owned_by": "glm-asr"
    }
  ]
}
```

### GET `/health`

健康检查。

```bash
curl http://localhost:9930/health
```

响应：

```json
{
  "status": "ok",
  "model_loaded": true
}
```

## 错误码

| HTTP 状态码 | 含义 |
|-------------|------|
| 400 | 请求格式错误，缺少 audio_url |
| 500 | 模型推理失败，详情见 `detail` 字段 |
| 503 | 模型尚未加载完成 |

错误响应示例：

```json
{
  "detail": "No audio_url provided. This API only supports audio transcription."
}
```

## 与 OpenAI API 的兼容性

本服务遵循 OpenAI Chat Completions 协议格式，可直接集成到支持 OpenAI API 的应用中：

- **api_key**：任意非空字符串即可（如 `EMPTY`）
- **base_url**：`http://<host>:9930/v1`
- **model**：`glm-asr`
- **content 类型**：使用 `audio_url` 传递音频（与 GPT-4o 音频接口格式一致）
