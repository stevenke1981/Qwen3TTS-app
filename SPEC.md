# Qwen3-TTS 桌面應用程式規格書

## 1. 專案概述

**專案名稱：** Qwen3-TTS Desktop  
**專案類型：** 桌面應用程式（PySide6）  
**核心功能：**
- 文字轉語音合成（Qwen3-TTS）
- 語音克隆（文字參考 + 音檔參考）
- 潤稿翻譯（多 LLM 提供商）
- 語音辨識（Qwen3-ASR，本地或遠端 API）
- 歷史記錄管理
- 集中式設定管理

**單一實例約束：** 應用程式透過 `QSharedMemory` 確保同時只有一個實例執行。

---

## 2. 技術架構

### 2.1 系統架構圖

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              GUI Layer (PySide6)                              │
│  ┌──────────────────────────────────────────────────────────────────────────┐ │
│  │                           QTabWidget (6 tabs)                            │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────┐ ┌───────┐  │ │
│  │  │ 文字合成  │ │ 語音克隆  │ │ 潤稿翻譯  │ │ 語音辨識  │ │歷史│ │ 設定  │  │ │
│  │  │ TextTab  │ │CloneTab  │ │ EditTab  │ │ ASRTab   │ │    │ │       │  │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────┘ └───────┘  │ │
│  └──────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                               Service Layer                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │  AudioPlayer    │  │  AudioExporter  │  │ HistoryManager  │              │
│  │  (QtMultimedia) │  │   (soundfile)   │  │    (YAML)       │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │  Qwen3Client    │  │   LLMClient     │  │   ASRClient     │              │
│  │  (requests)     │  │  (requests)     │  │  (requests /    │              │
│  └─────────────────┘  └─────────────────┘  │   subprocess)   │              │
│  ┌─────────────────┐                        └─────────────────┘              │
│  │ChineseConverter │                                                          │
│  │   (opencc)      │                                                          │
│  └─────────────────┘                                                          │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              Backend Services                                │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌────────────────────┐ │
│  │   Qwen3-TTS API      │  │     LLM API          │  │  Qwen3-ASR         │ │
│  │ (文字合成/語音克隆)    │  │ (潤稿/翻譯)          │  │  ─ 本地 venv-asr   │ │
│  │ localhost:8000        │  │ Ollama/OpenAI/FastAPI│  │  ─ 遠端 API        │ │
│  │ (scripts/tts_server) │  │ localhost:11434 等   │  │    (OpenAI-compat) │ │
│  └──────────────────────┘  └──────────────────────┘  └────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 模組依賴關係

```
main.py  (QSharedMemory 單一實例鎖 + ServerManager 生命週期)
    ├── _check_and_download_models()
    │       └── ModelDownloadWorker (QThread)
    ├── ServerManager
    │       ├── _ManagedServer("TTS", venv-tts, tts_server.py)
    │       └── _ManagedServer("LLM", venv-llm, llm_server.py)
    └── MainWindow
            ├── TextTab
            │       ├── Qwen3Client
            │       ├── AudioPlayer
            │       ├── AudioExporter
            │       └── HistoryManager
            ├── CloneTab
            │       ├── Qwen3Client
            │       ├── AudioPlayer
            │       ├── AudioExporter
            │       └── HistoryManager
            ├── EditTab
            │       ├── LLMClient (Ollama / OpenAI / FastAPI)
            │       ├── ChineseConverter
            │       ├── Qwen3Client
            │       └── HistoryManager
            ├── ASRTab
            │       └── ASRClient
            │               ├── [local] venv-asr subprocess
            │               │          └── scripts/asr_worker.py
            │               └── [api]   遠端 OpenAI-compatible 端點
            ├── HistoryTab
            │       └── HistoryManager
            └── SettingsTab  (QTabWidget: TTS / LLM / ASR / 音訊UI / 系統)
                    ├── Config
                    ├── ASRClient  (同步 mode/api_url/api_key)
                    ├── Qwen3Client (測試連線)
                    └── LLMClient   (測試連線)
```

---

## 3. 功能規格

### 3.1 文字合成（Text-to-Speech）

| 功能 | 說明 |
|------|------|
| 文字輸入 | 多行文字輸入框 |
| 語速調整 | 0.5x ~ 2.0x，預設 1.0x |
| 音調調整 | 0.5x ~ 2.0x，預設 1.0x |
| 音量調整 | 0.0 ~ 1.0，預設 1.0 |
| 播放控制 | 播放 / 暫停 / 停止 |
| 音訊匯出 | WAV 格式 |
| 快速潤稿 | 一鍵將輸入文字送往潤稿翻譯分頁 |

### 3.2 語音克隆（Voice Clone）

| 功能 | 說明 |
|------|------|
| 模式一：文字參考 | 輸入參考文字，使用相同音色朗讀目標文字 |
| 模式二：音檔參考 | 上傳參考音檔（.wav / .mp3），克隆該音色 |
| 語速調整 | 0.5x ~ 2.0x，預設 1.0x |
| 音量調整 | 0.0 ~ 1.0，預設 1.0 |
| 播放控制 | 播放 / 暫停 / 停止 |
| 音訊匯出 | WAV 格式 |

### 3.3 潤稿翻譯（Edit & Translate）

| 功能 | 說明 |
|------|------|
| 原文輸入 | 多行文字輸入框 |
| 七種處理模式 | 見下表 |
| 快速轉換 | 結果一鍵送往文字合成或語音克隆 |
| LLM 多提供商 | Ollama / OpenAI-compatible / FastAPI |

**處理模式：**

| 模式 | 說明 | 後端 |
|------|------|------|
| 潤稿 | 優化語句流暢度 | LLMClient |
| 中文簡→繁 | 簡體轉繁體 | ChineseConverter (opencc) |
| 中文繁→簡 | 繁體轉簡體 | ChineseConverter (opencc) |
| 英→中翻譯 | English → 中文 | LLMClient |
| 中→英翻譯 | 中文 → English | LLMClient |
| 日→中翻譯 | 日文 → 中文 | LLMClient |
| 自訂指令 | 使用者自訂 Prompt | LLMClient |

### 3.4 語音辨識（ASR）

| 功能 | 說明 |
|------|------|
| 來源：本地檔案 | 音訊 / 影片檔案（wav, mp3, mp4 等） |
| 來源：線上 URL | YouTube / Bilibili 等 |
| 引擎：本地 | 透過 venv-asr 執行 Qwen3-ASR |
| 引擎：遠端 API | OpenAI-compatible `/v1/audio/transcriptions` |
| 語言 | 自動偵測或指定（30+ 語言） |
| 模型選擇 | Qwen3-ASR-0.6B / Qwen3-ASR-1.7B |
| 時間戳記 | 詞語級別時間軸（ForcedAligner） |
| 匯出格式 | TXT / SRT / VTT |
| 進度顯示 | 即時顯示下載 / 載入 / 辨識進度 |

### 3.5 歷史記錄（History）

| 功能 | 說明 |
|------|------|
| 瀏覽記錄 | 清單檢視所有歷史項目 |
| 操作類型 | TTS / Clone / Edit |
| 詳情檢視 | 完整內容 |
| 重新執行 | 快速重複操作 |
| 刪除 | 單筆或清空全部 |
| 複製文字 | 複製到剪貼簿 |

### 3.6 設定（Settings）— 分頁式佈局（v0.4.0）

**TTS 設定分頁：**

| 群組 | 欄位 | 說明 |
|------|------|------|
| 本地伺服器 | 模型 ID | TTS 模型（預設 Qwen/Qwen3-TTS-0.6B） |
| | 裝置 | cpu / cuda / mps |
| | 連接埠 | 伺服器埠號（預設 8000） |
| | 自動啟動 | 啟動 app 時自動啟動 TTS 伺服器 |
| API 設定 | API URL | TTS 伺服器位址（預設 `localhost:8000`） |
| | 超時時間 | 10–300 秒 |
| | SSL 驗證 | 是否驗證 SSL 憑證 |

**LLM 設定分頁：**

| 群組 | 欄位 | 說明 |
|------|------|------|
| 本地伺服器 | 模型 ID | LLM 模型（預設 Qwen3-0.6B） |
| | 裝置 | cpu / cuda / mps |
| | 連接埠 | 伺服器埠號（預設 8001） |
| | 自動啟動 | 啟動 app 時自動啟動 LLM 伺服器 |
| API 設定 | 提供商 | `fastapi` / `ollama` / `openai` |
| | Base URL | LLM 伺服器位址 |
| | API Key | Bearer Token |
| | 模型 | 模型 ID |

**ASR 設定分頁：**

| 群組 | 欄位 | 說明 |
|------|------|------|
| 模式 | 模式選擇 | `local`（本地 venv-asr）/ `api`（遠端 API） |
| API | API URL | 遠端 ASR 端點 |
| | API Key | Bearer Token |

**音訊/UI 分頁：**

| 欄位 | 說明 |
|------|------|
| 取樣率 | 唯讀顯示 |
| 格式 | 唯讀顯示 |
| 視窗大小 | 寬 × 高 |
| 主題 | dark / light |

**系統資訊分頁：**

| 欄位 | 說明 |
|------|------|
| 版本 | 應用程式版本號 |
| Python | Python 版本 |
| 平台 | 作業系統 |
| GPU | CUDA/MPS/CPU 資訊 |
| 模型狀態 | 各模型下載狀態 |
| 伺服器健康 | TTS/LLM 伺服器即時 /health 檢查 |

**測試按鈕：** 每個分頁內建「測試連線」按鈕  
**底部工具列：** 匯出組態 / 匯入組態 / 儲存

---

## 4. API 介面規格

### 4.1 Qwen3-TTS Server（`scripts/tts_server.py`，port 8000）

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/health` | 健康檢查 → `{"status":"ok","model":"...","device":"..."}` |
| POST | `/tts` | 文字合成 → Binary audio |
| POST | `/clone/text` | 語音克隆（文字參考）→ Binary audio |
| POST | `/clone/audio` | 語音克隆（音檔參考，base64）→ Binary audio |

```
POST /tts
{ "text": "...", "speed": 1.0, "pitch": 1.0, "volume": 1.0, "format": "wav", "speaker": null }

POST /clone/text
{ "text": "...", "ref_text": "...", "speed": 1.0, ... }

POST /clone/audio
{ "text": "...", "ref_audio": "<base64>", "speed": 1.0, ... }
```

### 4.2 LLM API

> 本地模式可選擇：
> - **Ollama**（需另外安裝 Ollama）
> - **本地 LLM 伺服器**（`scripts/llm_server.py`，使用 `models/` 下的 Qwen3 模型，設定 `provider: fastapi`）
> - **外部 OpenAI-compatible API**

**Ollama 模式：**
```
POST {base_url}/api/generate
{ "model": "llama3.2:latest", "prompt": "...", "stream": false }
→ { "response": "..." }

GET {base_url}/api/tags  (健康檢查 / 列出模型)
```

**OpenAI / FastAPI 模式：**
```
POST {base_url}/v1/chat/completions
Authorization: Bearer {api_key}
{ "model": "...", "messages": [...], "stream": false }
→ { "choices": [{ "message": { "content": "..." } }] }

GET {base_url}/v1/models  (健康檢查 / 列出模型)
```

### 4.3 Qwen3-ASR API（遠端 API 模式）

```
POST {api_url}/v1/audio/transcriptions
Authorization: Bearer {api_key}  (可選)
Content-Type: multipart/form-data
  file:            <audio bytes>
  model:           "Qwen/Qwen3-ASR-0.6B"
  response_format: "verbose_json"
  language:        "Chinese"  (可選，留空為自動偵測)

→ {
    "text": "完整辨識文字",
    "language": "Chinese",
    "segments": [{ "text": "...", "start": 0.0, "end": 2.5 }, ...]
  }
```

### 4.4 ASR 本地 Subprocess 協定

**stdin（JSON）：**
```json
{
  "type":       "file" | "url",
  "source":     "/path/to/audio" | "https://...",
  "model_id":   "Qwen/Qwen3-ASR-0.6B",
  "language":   "auto" | "Chinese" | "English" | ...,
  "timestamps": true,
  "device":     "cpu" | "cuda"
}
```

**stdout（JSON）：**
```json
{
  "status":   "ok" | "error",
  "text":     "辨識結果",
  "language": "Chinese",
  "segments": [{ "text": "...", "start": 0.0, "end": 2.5 }],
  "error":    null
}
```

**stderr：** `PROGRESS:<stage>` 進度標籤

---

## 5. 設定檔（`config.yaml`）

```yaml
api:
  qwen3_base_url: "http://localhost:8000"
  qwen3_timeout: 60
  verify_ssl: true

tts_server:
  model_id: "Qwen/Qwen3-TTS-0.6B"
  device: "cpu"
  port: 8000
  auto_start: true

llm_server:
  model_id: "Qwen3-0.6B"
  device: "cpu"
  port: 8001
  auto_start: true

ollama:
  base_url: "http://localhost:11434"
  default_model: "llama3.2:latest"

llm:
  provider: "fastapi"              # "ollama" | "openai" | "fastapi"
  base_url: "http://localhost:8001"
  api_key: ""
  model: "Qwen3-0.6B"

audio:
  sample_rate: 22050
  format: "wav"

ui:
  theme: "dark"
  window_size: [960, 640]

history:
  max_entries: 100

asr:
  venv_asr_path: "venv-asr"
  model_id: "Qwen/Qwen3-ASR-0.6B"
  device: "cpu"
  timestamps: true
  mode: "local"               # "local" | "api"
  api_url: ""
  api_key: ""
```

---

## 6. 專案結構

```
Qwen3TTS-app/
├── app/
│   ├── __init__.py
│   ├── main.py                  # 入口點，QSharedMemory 單一實例鎖
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py       # 主視窗，6 分頁，狀態列連線指示燈
│   │   ├── text_tab.py          # 文字合成分頁
│   │   ├── clone_tab.py         # 語音克隆分頁
│   │   ├── edit_tab.py          # 潤稿翻譯分頁
│   │   ├── asr_tab.py           # 語音辨識分頁
│   │   ├── history_tab.py       # 歷史記錄分頁
│   │   ├── settings_tab.py      # 設定分頁（TTS / LLM / ASR / 音訊UI / 系統，QTabWidget）
│   │   ├── waveform_widget.py   # 波形視覺化 Widget
│   │   └── theme.py             # 主題 tokens（dark / light 模式）
│   ├── api/
│   │   ├── __init__.py
│   │   ├── qwen3_client.py      # Qwen3-TTS HTTP 客戶端
│   │   ├── ollama_client.py     # Ollama 客戶端（舊版相容）
│   │   ├── llm_client.py        # 統一 LLM 客戶端（Ollama/OpenAI/FastAPI）
│   │   ├── asr_client.py        # ASR 橋接（subprocess / 遠端 API）
│   │   └── exceptions.py        # 自訂例外
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── player.py            # QMediaPlayer 封裝
│   │   ├── exporter.py          # WAV/MP3 匯出
│   │   └── concatenator.py      # 多段音訊拼接（v0.3.0）
│   └── core/
│       ├── __init__.py
│       ├── config.py            # Dataclass 設定管理（YAML）
│       ├── history.py           # 歷史記錄管理（YAML）
│       ├── presets.py           # 語音預設管理
│       ├── drafts.py            # 草稿自動存取
│       ├── chinese_converter.py # 簡繁轉換（opencc）
│       ├── ssml.py              # SSML 標記輔助函式（v0.3.0）
│       ├── duration_estimator.py # 即時時長預估（v0.3.0）
│       ├── recent_texts.py      # 最近使用文字佇列（v0.3.0）
│       ├── i18n.py              # 多語言 UI 字串表（v0.3.0）
│       ├── app_logger.py        # 結構化日誌（v0.3.0）
│       ├── model_manager.py     # 模型偵測/下載管理（v0.4.0）
│       ├── server_manager.py    # TTS/LLM 伺服器子程序管理（v0.4.0）
│       └── text_templates.py    # 文字範本庫（v0.4.0）
├── scripts/
│   ├── asr_worker.py            # ASR subprocess worker（venv-asr 下執行）
│   ├── tts_server.py            # Qwen3-TTS FastAPI 伺服器（venv-tts 下執行）
│   ├── llm_server.py            # 本地 LLM FastAPI 伺服器（venv-llm 下執行）
│   ├── download_models.py       # 模型下載腳本（互動式選單）
│   ├── setup.py                 # 統一環境建立（Python，取代 bat/sh）
│   └── start.py                 # 統一啟動腳本（Python）
├── models/                      # 本地模型目錄（git 忽略，由 download_models.bat 建立）
│   ├── Qwen3-ASR-0.6B/          # 語音辨識模型（小）
│   ├── Qwen3-ASR-1.7B/          # 語音辨識模型（大）
│   ├── Qwen3-ForcedAligner-0.6B/ # 時間軸對齊模型
│   ├── Qwen3-TTS-0.6B/          # 語音合成模型（小）
│   ├── Qwen3-TTS-1.7B/          # 語音合成模型（大）
│   ├── Qwen3-0.6B/              # LLM 潤稿翻譯（超小）
│   ├── Qwen3-1.7B/              # LLM 潤稿翻譯（小型）
│   └── Qwen3-4B/                # LLM 潤稿翻譯（中型）
├── data/
│   ├── history.yaml             # 歷史記錄持久化
│   ├── presets.yaml             # 自訂語音預設
│   └── drafts.yaml              # 草稿自動存取
├── tests/                       # pytest 測試套件
│   ├── test_config.py
│   ├── test_presets.py
│   ├── test_drafts.py
│   ├── test_history.py
│   ├── test_chinese_converter.py
│   ├── test_ssml.py             # SSML 標記測試（v0.3.0）
│   ├── test_concatenator.py     # 音訊拼接測試（v0.3.0）
│   ├── test_duration_estimator.py # 時長預估測試（v0.3.0）
│   ├── test_recent_texts.py     # 最近文字測試（v0.3.0）
│   ├── test_i18n.py             # 多語言測試（v0.3.0）
│   ├── test_app_logger.py       # 日誌測試（v0.3.0）
│   ├── test_text_templates.py   # 文字範本測試（v0.4.0）
│   ├── test_model_manager.py    # 模型管理測試（v0.4.0）
│   └── test_server_manager.py   # 伺服器管理測試（v0.4.0）
├── venv/                        # 主 GUI 虛擬環境（git 忽略）
├── venv-asr/                    # ASR 虛擬環境（git 忽略）
├── venv-tts/                    # TTS 虛擬環境（git 忽略）
├── venv-llm/                    # LLM 虛擬環境（git 忽略）
├── requirements.txt             # 主 venv 依賴
├── requirements-asr.txt         # venv-asr 依賴
├── requirements-tts.txt         # venv-tts 依賴
├── requirements-llm.txt         # venv-llm 依賴
├── config.yaml                  # 執行期設定（git 忽略）
├── config.example.yaml          # 設定範本
├── pyproject.toml               # ruff + pytest 配置
├── plan.md                      # 版本實作計畫
├── SPEC.md
└── README.md
```

---

## 7. 依賴套件

### 主 venv（`requirements.txt`）

| 套件 | 版本 | 用途 |
|------|------|------|
| PySide6 | >=6.6.0 | GUI 框架 |
| pydantic | >=2.0.0 | 資料驗證 |
| PyYAML | >=6.0 | 設定檔讀寫 |
| requests | >=2.31.0 | HTTP 客戶端 |
| soundfile | >=0.12.0 | 音訊處理 |
| numpy | >=1.24.0 | 音訊資料 |
| opencc | >=1.2.0 | 簡繁轉換 |

### venv-asr（`requirements-asr.txt`）

| 套件 | 用途 |
|------|------|
| torch / torchaudio | 推論 |
| transformers | Qwen3-ASR 模型載入 |
| huggingface_hub | 模型下載 |
| yt-dlp | YouTube 音訊下載 |
| ffmpeg-python | 音訊解碼 |

### venv-tts（`requirements-tts.txt`）

| 套件 | 用途 |
|------|------|
| qwen-tts | Qwen3-TTS 模型 |
| fastapi / uvicorn | HTTP 伺服器 |
| torch / torchaudio | 推論 |
| soundfile | 音訊輸出 |

### venv-llm（`requirements-llm.txt`）

| 套件 | 用途 |
|------|------|
| transformers | Qwen3 LLM 載入與推論 |
| accelerate | 多設備支援 |
| fastapi / uvicorn | HTTP 伺服器 |
| torch | 推論 |
| sentencepiece / protobuf | Tokenizer |

---

## 8. 實作狀態

| 功能 | 狀態 | 說明 |
|------|------|------|
| 文字合成分頁 | ✅ | 完整實作 |
| 語音克隆分頁 | ✅ | 文字 + 音檔參考 |
| 潤稿翻譯分頁 | ✅ | 7 種模式，多 LLM 提供商 |
| 語音辨識分頁 | ✅ | 本地 venv-asr + 遠端 API |
| 歷史記錄分頁 | ✅ | 完整實作 |
| 設定分頁 | ✅ | TTS / LLM / ASR / UI 設定 |
| 單一實例約束 | ✅ | QSharedMemory |
| ASR 設定集中到 Settings | ✅ | 可在設定儲存並即時同步 |
| TTS 本地伺服器 | ✅ | `scripts/tts_server.py` |
| ASR subprocess worker | ✅ | `scripts/asr_worker.py` |
| LLM 本地伺服器 | ✅ | `scripts/llm_server.py`（venv-llm） |
| 模型下載腳本 | ✅ | `download_models.bat` / `scripts/download_models.py` |
| 本地模型路徑解析 | ✅ | `models/` 優先，fallback HF cache |
| 深色主題 | ✅ | 全局 QSS dark theme |
| 狀態列連線指示燈 | ✅ | Qwen3 / LLM 連線狀態 |

### v0.2.0 新增功能

| 功能 | 狀態 | 說明 |
|------|------|------|
| 批次 TTS 合成 | ✅ | 按段落拆分、逐段合成，匯出 `part_001.wav` 等 |
| 波形視覺化 | ✅ | `WaveformWidget` — 合成完成即顯示波形 |
| 語音預設 | ✅ | 5 個內建 + 自訂預設（`data/presets.yaml`） |
| 拖放匯入 | ✅ | 拖放 `.txt` / `.md` / `.srt` 到 TextTab |
| 系統匣 | ✅ | 最小化到系統匣，右鍵選單（顯示/退出） |
| 文字統計 | ✅ | 即時字數 / 行數 / 中文字數統計 |
| 克隆音調滑桿 | ✅ | CloneTab 新增 pitch 0.5–2.0 調整 |
| 快捷鍵覆蓋 | ✅ | F1 顯示全快捷鍵表，Ctrl+Q 強制退出 |
| 自動存草稿 | ✅ | 2 秒防抖自動存 / 啟動恢復（`data/drafts.yaml`） |
| 統一 Python 腳本 | ✅ | `scripts/setup.py` / `scripts/start.py` 取代 bat/sh |

### v0.2.0 品質改善

| 項目 | 說明 |
|------|------|
| ruff linting | 全部通過（pyproject.toml 配置 py310, line-length 100） |
| pytest 測試 | 52 tests（config, presets, drafts, history, chinese_converter） |
| B904 修復 | 所有 `raise` 改為 `raise ... from exc` |
| Signal 修正 | EditTab Signal 宣告移至 class 頂層 |

### v0.3.0 新增功能

| 功能 | 狀態 | 模組 | 說明 |
|------|------|------|------|
| SSML 標記編輯器 | ✅ | `app/core/ssml.py` | 工具列插入 break/emphasis/prosody/phoneme 標記 |
| 音訊拼接器 | ✅ | `app/audio/concatenator.py` | 批次合成後自動拼接為單一 WAV |
| 即時時長預估 | ✅ | `app/core/duration_estimator.py` | 根據字數與語速即時預估合成時長 |
| 匯出格式選擇器 | ✅ | TextTab / CloneTab | 匯出支援 WAV / MP3 格式選擇 |
| 最近使用文字 | ✅ | `app/core/recent_texts.py` | 記錄最近 20 筆合成文字，一鍵載入 |
| A/B 比較播放 | ✅ | TextTab | 保留前次結果，A/B 切換比較 |
| 批次進度百分比 | ✅ | TextTab | 顯示 N/M (pct%) 確定進度 |
| 多語言 UI 框架 | ✅ | `app/core/i18n.py` | zh-TW / en 字串表，~90 鍵，t() 函式 |
| 組態匯出/匯入 | ✅ | SettingsTab | 匯出 / 匯入 YAML 設定檔 |
| 日誌檢視器 | ✅ | `app/core/app_logger.py` | RotatingFileHandler + F12 檢視面板 |

### v0.3.0 品質改善

| 項目 | 說明 |
|------|------|
| ruff linting | 全部通過 |
| pytest 測試 | 99 passed, 1 skipped（11 個測試檔） |
| 移除 bat/sh 腳本 | 統一使用 `scripts/setup.py` / `scripts/start.py` |
| 預設本地部署 | 所有 config 預設指向 localhost |
| Config.from_yaml | 修復空 YAML 檔案 `NoneType` 錯誤 |

### v0.4.0 新增功能

| 功能 | 狀態 | 模組 | 說明 |
|------|------|------|------|
| 模型自動安裝 | ✅ | `app/core/model_manager.py` | 啟動時偵測缺失的 0.6B 模型，自動下載（QThread + 進度對話框） |
| 伺服器自動啟動 | ✅ | `app/core/server_manager.py` | 自動啟動 TTS/LLM 本地 FastAPI 伺服器子程序 |
| 分頁式設定 | ✅ | `app/ui/settings_tab.py` | QTabWidget 5 分頁：TTS 設定 / LLM 設定 / ASR 設定 / 音訊 UI / 系統資訊 |
| 本地優先組態 | ✅ | `app/core/config.py` | 新增 TTSServerConfig / LLMServerConfig，LLM 預設指向 localhost:8001 FastAPI |
| 文字範本庫 | ✅ | `app/core/text_templates.py` | 6 個預設中文範本 + 自訂範本 CRUD + JSON 持久化 |
| 明亮主題 | ✅ | `app/ui/theme.py` | `apply_theme(app, mode="light")` 明亮模式，可在設定切換 |
| 健康狀態儀表板 | ✅ | `app/ui/settings_tab.py` | 系統資訊分頁：版本 / Python / GPU / 模型狀態 / 伺服器即時健康檢查 |
| 伺服器生命週期管理 | ✅ | `app/main.py` | 啟動時 start_all()，關閉時 stop_all()，atexit 保險清理 |
| 設定匯出/匯入擴充 | ✅ | `app/ui/settings_tab.py` | 匯出/匯入包含 tts_server 和 llm_server 新欄位 |
| GPU 資訊偵測 | ✅ | `app/core/model_manager.py` | `get_gpu_info()` 偵測 CUDA/MPS/CPU 並回報 VRAM |

### v0.4.0 品質改善

| 項目 | 說明 |
|------|------|
| ruff linting | 全部通過 |
| pytest 測試 | 116 passed, 1 skipped（14 個測試檔） |
| main.py 錯誤修復 | ServerManager 建構參數改為使用 config 欄位具名傳入 |
| 組態一致性 | TTSServerConfig / LLMServerConfig 在 from_yaml / to_yaml / settings_tab 均正確處理 |

---

## 9. 新增檔案（v0.2.0）

```
app/ui/waveform_widget.py     # 波形視覺化 Widget
app/core/presets.py            # 語音預設管理
app/core/drafts.py             # 草稿自動存取
scripts/setup.py               # 統一環境建立腳本
scripts/start.py               # 統一啟動腳本
pyproject.toml                 # ruff + pytest 配置
tests/                         # 測試套件
├── __init__.py
├── test_config.py
├── test_presets.py
├── test_drafts.py
├── test_history.py
└── test_chinese_converter.py
```

## 10. 新增檔案（v0.4.0）

```
app/core/model_manager.py      # 模型偵測/下載管理（ModelInfo, ModelDownloadWorker）
app/core/server_manager.py     # TTS/LLM 伺服器子程序管理（_ManagedServer, ServerManager）
app/core/text_templates.py     # 文字範本庫（TextTemplate, TemplateStore）
tests/test_text_templates.py   # 文字範本測試
tests/test_model_manager.py    # 模型管理測試
tests/test_server_manager.py   # 伺服器管理測試
```


## 11. v0.4.1 更新（Bug 修復 + 10 項實用功能）

### 修復項目

| 問題 | 修復位置 |
|------|---------|
| 啟動時 QObject 跨執行緒建立子物件崩潰 | app/main.py — 改用 QEventLoop + QThread 模式 |
| huggingface_hub 未安裝導致模型下載失敗 | requirements.txt 新增 huggingface_hub>=0.23.0 |
| ModelDownloadWorker 下載完成後未發送最終進度訊號 | app/core/model_manager.py |
| QMessageBox.Yes 已棄用引發 AttributeError | history_tab.py + main.py — 改用 StandardButton.Yes |
| WaveformWidget._drag_x 未初始化 | app/ui/waveform_widget.py — __init__ 加入初始化 |
| closeEvent 重複定義 | app/ui/main_window.py — 合併為單一方法 |
| text_tab.py _on_copy_audio_path 使用未導入的 QtWidgets | 改用已導入的 QApplication |

### 新增功能

| 功能 | 位置 | 說明 |
|------|------|------|
| HuggingFace 鏡像支援 | app/core/model_manager.py | 讀取 HF_ENDPOINT 環境變數 |
| 視窗幾何持久化 | app/ui/main_window.py | 關閉時儲存位置/大小，重開時還原 |
| 歷史紀錄 CSV 匯出 | app/ui/history_tab.py | 「匯出 CSV」按鈕，utf-8-sig 編碼 |
| 文字尋找與取代 | app/ui/text_tab.py | _FindReplaceDialog 類別，Ctrl+H 快捷鍵 |
| 開啟模型資料夾按鈕 | app/ui/settings_tab.py | 跨平台開啟 models/ 目錄 |
| 插入範例文字按鈕 | app/ui/text_tab.py | 插入中文範例文字 |
| 波形視圖縮放平移 | app/ui/waveform_widget.py | 滾輪縮放，水平拖曳平移 |
| ASR 自動標點模組 | app/core/auto_punctuation.py | 純 Python 啟發式標點補全，整合至 ASR Tab |
| 複製音訊路徑按鈕 | app/ui/text_tab.py | 合成後複製匯出路徑至剪貼簿 |
| 批次合成百分比顯示 | app/ui/text_tab.py | 進度列顯示 n/total (pct%) |

### 新增檔案（v0.4.1）

- app/core/auto_punctuation.py — ASR 後處理自動標點模組
- tests/test_auto_punctuation.py — 18 項測試

### 品質

| 項目 | 結果 |
|------|------|
| ruff | 全部通過 |
| pytest | 133 passed, 1 skipped（15 個測試檔） |
