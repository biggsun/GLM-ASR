# API 文档

GLM-ASR 提供两组 OpenAI 兼容接口：

| 接口 | 用途 | 协议 |
|------|------|------|
| `/v1/audio/transcriptions` | 语音转文字（Whisper API） | multipart/form-data |
| `/v1/chat/completions` | Chat Completions 音频识别 | JSON |

---

## 一、Whisper API（推荐）

### POST `/v1/audio/transcriptions`

兼容 OpenAI Whisper 转录接口，通过文件上传进行语音识别。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | file | 是 | 音频文件（mp3/mp4/mpeg/mpga/m4a/wav/webm） |
| `model` | string | 否 | 模型名称，默认 `glm-asr` |
| `response_format` | string | 否 | 响应格式：`json`/`text`/`srt`/`vtt`/`verbose_json`，默认 `json` |
| `prompt` | string | 否 | 提示文本，可辅助识别准确率 |
| `language` | string | 否 | 音频语言（ISO 639-1），如 `zh`、`en` |

#### Python 示例（OpenAI SDK）

```bash
pip install openai
```

```python
from openai import OpenAI

client = OpenAI(api_key="EMPTY", base_url="http://localhost:9930/v1")

# 基础用法
with open("audio.wav", "rb") as f:
    transcription = client.audio.transcriptions.create(
        model="glm-asr",
        file=f
    )
print(transcription.text)

# 指定格式和提示
with open("audio.wav", "rb") as f:
    transcription = client.audio.transcriptions.create(
        model="glm-asr",
        file=f,
        response_format="verbose_json",
        language="zh",
        prompt="这是一段中文会议录音"
    )
print(transcript.text)
```

#### curl 示例

```bash
# json 格式（默认）
curl http://localhost:9930/v1/audio/transcriptions \
  -F file=@audio.wav \
  -F model=glm-asr

# 纯文本
curl http://localhost:9930/v1/audio/transcriptions \
  -F file=@audio.wav \
  -F model=glm-asr \
  -F response_format=text

# SRT 字幕
curl http://localhost:9930/v1/audio/transcriptions \
  -F file=@audio.wav \
  -F model=glm-asr \
  -F response_format=srt

# VTT 字幕
curl http://localhost:9930/v1/audio/transcriptions \
  -F file=@audio.wav \
  -F model=glm-asr \
  -F response_format=vtt

# 详细 JSON（含时长、分段信息）
curl http://localhost:9930/v1/audio/transcriptions \
  -F file=@audio.wav \
  -F model=glm-asr \
  -F response_format=verbose_json
```

#### 响应格式

**json（默认）**

```json
{"text": "转录文本内容"}
```

**text**

```
转录文本内容
```

**srt**

```
1
00:00:00,000 --> 00:00:06,000
转录文本内容
```

**vtt**

```
WEBVTT

00:00:00.000 --> 00:00:06.000
转录文本内容
```

**verbose_json**

```json
{
  "task": "transcribe",
  "language": "unknown",
  "duration": 6.0,
  "text": "转录文本内容",
  "segments": [
    {
      "id": 0,
      "seek": 0,
      "start": 0.0,
      "end": 6.0,
      "text": "转录文本内容",
      "tokens": [],
      "temperature": 0.0,
      "avg_logprob": 0.0,
      "compression_ratio": 0.0,
      "no_speech_prob": 0.0
    }
  ]
}
```

---

## 二、Chat Completions API

### POST `/v1/chat/completions`

通过 OpenAI Chat Completions 协议进行音频识别，音频通过 `audio_url` 传递。

#### Python 示例

```python
from openai import OpenAI
import base64

client = OpenAI(api_key="EMPTY", base_url="http://localhost:9930/v1")

with open("audio.wav", "rb") as f:
    audio_b64 = base64.b64encode(f.read()).decode()

response = client.chat.completions.create(
    model="glm-asr",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "audio_url", "audio_url": {"url": f"data:audio/wav;base64,{audio_b64}"}},
                {"type": "text", "text": "Please transcribe this audio into text"}
            ]
        }
    ],
    max_tokens=1024
)
print(response.choices[0].message.content)
```

#### curl 示例

```bash
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

#### 音频 URL 格式

| 格式 | 示例 |
|------|------|
| Base64 | `data:audio/wav;base64,UklGRi...` |
| HTTP URL | `http://example.com/audio.wav` |
| HTTPS URL | `https://example.com/audio.mp3` |

---

## 辅助接口

### GET `/v1/models`

```bash
curl http://localhost:9930/v1/models
```

```json
{"object": "list", "data": [{"id": "glm-asr", "object": "model", "created": 1779284806, "owned_by": "glm-asr"}]}
```

### GET `/health`

```bash
curl http://localhost:9930/health
```

```json
{"status": "ok", "model_loaded": true}
```

---

## 错误码

| HTTP 状态码 | 含义 |
|-------------|------|
| 400 | 请求参数错误 |
| 500 | 模型推理失败 |
| 503 | 模型尚未加载完成 |

---

## 兼容性说明

- **api_key**：任意非空字符串（如 `EMPTY`）
- **base_url**：`http://<host>:9930/v1`
- **model**：`glm-asr`
- 支持的音频格式：mp3、mp4、mpeg、mpga、m4a、wav、webm
- 支持 17 种语言的语音识别
