# Docker Compose 部署指南

## 1. 环境准备

### 1.1 安装 Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

### 1.2 安装 NVIDIA Container Toolkit

```bash
# 添加仓库
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# 安装
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# 配置 Docker 运行时
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### 1.3 验证 GPU 可用

```bash
docker run --rm --gpus all nvidia/cuda:13.0.0-base-ubuntu22.04 nvidia-smi
```

### 1.4 硬件要求

| 项目 | 要求 |
|------|------|
| GPU | NVIDIA GPU，>= 4GB 显存（推荐 RTX 3090 或更高） |
| 驱动 | >= 570.x（支持 CUDA 13.0） |
| 磁盘 | >= 10GB 可用空间（模型约 3GB + Docker 镜像约 6GB） |
| 内存 | >= 8GB |

## 2. 部署服务

### 2.1 克隆项目

```bash
git clone https://github.com/zai-org/GLM-ASR.git
cd GLM-ASR
```

### 2.2 启动服务（HuggingFace 源）

```bash
docker-compose up -d
```

### 2.3 启动服务（ModelScope 源，国内推荐）

```bash
MODEL_SOURCE=modelscope docker-compose up -d
```

### 2.4 使用 HuggingFace 镜像站

```bash
HF_ENDPOINT=https://hf-mirror.com docker-compose up -d
```

### 2.5 检查服务状态

```bash
# 查看启动日志（首次启动需下载模型，约 3GB，耗时视网络情况）
docker-compose logs -f glm-asr
```

等待日志出现以下内容即表示服务就绪：

```
INFO:     Uvicorn running on http://0.0.0.0:9930 (Press CTRL+C to quit)
```

验证服务：

```bash
curl http://localhost:9930/v1/models
# 预期返回: {"object":"list","data":[{"id":"glm-asr",...}]}
```

## 3. API 调用

服务启动后，提供 OpenAI 兼容的 `/v1/chat/completions` 接口，端口 `9930`。

### 3.1 Python 示例（OpenAI SDK）

```python
from openai import OpenAI
import base64

client = OpenAI(api_key="EMPTY", base_url="http://localhost:9930/v1")

# 方式一：使用 base64 编码的本地音频
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
print(response.choices[0].message.content.strip())

# 方式二：使用可访问的音频 URL
response = client.chat.completions.create(
    model="glm-asr",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "audio_url", "audio_url": {"url": "https://example.com/audio.wav"}},
                {"type": "text", "text": "Please transcribe this audio into text"}
            ]
        }
    ],
    max_tokens=1024
)
print(response.choices[0].message.content.strip())
```

### 3.2 curl 示例

```bash
# 使用 URL
curl http://localhost:9930/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-asr",
    "messages": [
      {
        "role": "user",
        "content": [
          {"type": "audio_url", "audio_url": {"url": "https://example.com/audio.wav"}},
          {"type": "text", "text": "Please transcribe this audio into text"}
        ]
      }
    ],
    "max_tokens": 1024
  }'

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
```

### 3.3 其他接口

```bash
# 查看可用模型
curl http://localhost:9930/v1/models

# 健康检查
curl http://localhost:9930/health
```

## 4. 环境变量说明

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MODEL_SOURCE` | `huggingface` | 模型下载源，可选 `huggingface` 或 `modelscope` |
| `MODEL_NAME` | `glm-asr` | OpenAI 兼容接口中的模型名称 |
| `HF_MODEL_ID` | `zai-org/GLM-ASR-Nano-2512` | HuggingFace 模型 ID |
| `MS_MODEL_ID` | `ZhipuAI/GLM-ASR-Nano-2512` | ModelScope 模型 ID |
| `HF_ENDPOINT` | 空 | HuggingFace 镜像站地址 |
| `PORT` | `9930` | 服务端口 |

## 5. 常用操作

```bash
# 停止服务
docker-compose down

# 重新构建（代码变更后）
docker-compose build --no-cache

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f glm-asr

# 清除模型缓存（重新下载模型）
docker volume rm glm-asr_model-cache
```

## 6. 技术架构

- 基础镜像：`nvidia/cuda:13.0`
- 推理引擎：PyTorch 2.9.1 + transformers 5.x
- API 框架：FastAPI + Uvicorn
- 音频处理：AutoProcessor + librosa + soundfile
- 支持音频格式：WAV、MP3、MP4 等
