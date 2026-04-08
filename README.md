# Qwen3-TTS Desktop

桌面版語音合成應用程式，基於 [Qwen3-TTS](https://github.com/QwenLM/Qwen3) 模型，提供文字轉語音、語音克隆、潤稿翻譯、語音辨識等功能。

## 功能

| 分頁 | 功能 |
|------|------|
| 文字合成 | 文字 → 語音，可調整語速 / 音調 / 音量，SSML 標記，批次合成，波形視覺化 |
| 語音克隆 | 以文字或音檔參考克隆音色後合成 |
| 潤稿翻譯 | 使用本地 LLM 潤稿、翻譯、繁簡轉換（Ollama / OpenAI / FastAPI） |
| 語音辨識 | Qwen3-ASR 本地 / API 模式，支援 20+ 語言，SRT/VTT 匯出 |
| 歷史記錄 | 瀏覽、重跑、刪除歷史合成記錄 |
| 設定 | TTS / LLM / ASR / UI 統一設定，匯出/匯入設定檔 |

## 系統需求

- Python 3.10+
- [Qwen3-TTS API server](https://github.com/QwenLM/Qwen3) 執行於 `localhost:8000`（本地模型或遠端 API）
- [Ollama](https://ollama.ai)（選用，潤稿翻譯功能）

## 快速開始

### 跨平台（Python）

```bash
# 首次啟動（建立環境 + 安裝依賴 + 啟動）
python scripts/start.py --setup

# 一般啟動
python scripts/start.py

# 只檢查服務連線
python scripts/start.py --check
```

### 環境管理

```bash
python scripts/setup.py app          # 主 GUI 環境
python scripts/setup.py tts          # TTS 模型伺服器環境
python scripts/setup.py asr          # ASR 模型環境
python scripts/setup.py llm          # LLM 模型伺服器環境
python scripts/setup.py all          # 全部環境
```

### 手動安裝

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

複製設定檔並依需求修改：

```bash
cp config.example.yaml config.yaml
```

啟動應用程式：

```bash
python -m app.main
```

## 設定

編輯 `config.yaml`（預設由 `config.example.yaml` 複製）：

```yaml
api:
  qwen3_base_url: "http://localhost:8000"  # Qwen3-TTS API 位址
  qwen3_timeout: 60

ollama:
  base_url: "http://localhost:11434"
  default_model: "llama3.2:latest"        # 潤稿翻譯使用的模型

audio:
  sample_rate: 22050
  format: "wav"

ui:
  window_size: [1200, 800]

history:
  max_entries: 100
```

## 依賴套件

| 套件 | 用途 |
|------|------|
| PySide6 | GUI 框架 |
| requests | HTTP API 呼叫 |
| soundfile | WAV 音訊讀寫 |
| PyYAML | 設定檔 / 歷史記錄 |
| opencc | 繁簡中文轉換 |
| pydantic | 資料驗證 |

> **MP3 匯出（選用）**：需額外安裝 `pydub` 與 [ffmpeg](https://ffmpeg.org)。

## 授權

MIT License
