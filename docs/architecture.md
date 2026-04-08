# Qwen3-TTS App — Architecture Knowledge Graph

> 自動產生於 v0.3.0　｜　最後更新: 2025-07

## 1. System Architecture

```mermaid
graph TB
    subgraph Entry["🚀 Entry Point"]
        main["app/main.py<br/>main()"]
    end

    subgraph UI["🖥️ UI Layer — PySide6"]
        MW["MainWindow<br/>QMainWindow"]
        TT["TextTab<br/>TTS 合成"]
        CT["CloneTab<br/>語音複製"]
        ET["EditTab<br/>文字處理"]
        AT["ASRTab<br/>語音辨識"]
        HT["HistoryTab<br/>歷史紀錄"]
        ST["SettingsTab<br/>設定"]
        TH["theme.py<br/>Dark Theme"]
        WF["WaveformWidget<br/>波形顯示"]
    end

    subgraph Core["⚙️ Core Layer"]
        CFG["config.py<br/>Config YAML"]
        HIS["history.py<br/>HistoryManager"]
        SSML["ssml.py<br/>SSML Tags"]
        DUR["duration_estimator.py<br/>時長預估"]
        REC["recent_texts.py<br/>最近文字"]
        I18N["i18n.py<br/>國際化"]
        LOG["app_logger.py<br/>Rotating Log"]
        CHN["chinese_converter.py<br/>OpenCC 繁簡轉換"]
        PRE["presets.py<br/>Voice Presets"]
        DRF["drafts.py<br/>Auto-save Drafts"]
    end

    subgraph Audio["🔊 Audio Layer"]
        PLY["player.py<br/>QMediaPlayer"]
        EXP["exporter.py<br/>WAV / MP3"]
        CAT["concatenator.py<br/>音訊拼接"]
    end

    subgraph API["🌐 API Client Layer"]
        Q3C["qwen3_client.py<br/>Qwen3 TTS REST"]
        LLM["llm_client.py<br/>Multi-Provider LLM"]
        OLL["ollama_client.py<br/>Ollama API"]
        ASR["asr_client.py<br/>ASR Local/Remote"]
        EXC["exceptions.py<br/>APIError / TTSError"]
    end

    subgraph Scripts["📡 Server Scripts"]
        TTS_S["tts_server.py<br/>FastAPI :8000"]
        LLM_S["llm_server.py<br/>FastAPI :8001"]
        ASR_W["asr_worker.py<br/>Subprocess stdin/out"]
        DL["download_models.py<br/>模型下載"]
    end

    subgraph Data["💾 Persistent Data"]
        YAML_CFG["config.yaml"]
        YAML_HIS["data/history.yaml"]
        YAML_REC["data/recent_texts.yaml"]
        YAML_DRF["data/drafts.yaml"]
        YAML_PRE["data/presets.yaml"]
        LOG_F["data/app.log"]
    end

    %% Entry → UI
    main --> MW
    main --> TH
    main --> CFG
    main --> Q3C
    main --> OLL
    main --> LLM
    main --> ASR
    main --> HIS

    %% MainWindow → Tabs
    MW --> TT
    MW --> CT
    MW --> ET
    MW --> AT
    MW --> HT
    MW --> ST
    MW --> LOG

    %% TextTab dependencies
    TT --> Q3C
    TT --> PLY
    TT --> EXP
    TT --> CAT
    TT --> WF
    TT --> SSML
    TT --> DUR
    TT --> REC
    TT --> PRE
    TT --> DRF
    TT --> HIS

    %% CloneTab dependencies
    CT --> Q3C
    CT --> PLY
    CT --> EXP
    CT --> HIS

    %% EditTab dependencies
    ET --> LLM
    ET --> OLL
    ET --> CHN
    ET --> HIS

    %% ASRTab dependencies
    AT --> ASR

    %% HistoryTab dependencies
    HT --> HIS

    %% SettingsTab dependencies
    ST --> CFG

    %% API → Servers
    Q3C -.->|HTTP :8000| TTS_S
    LLM -.->|HTTP :8001| LLM_S
    OLL -.->|HTTP :11434| LLM_S
    ASR -.->|subprocess| ASR_W

    %% Core → Data
    CFG --> YAML_CFG
    HIS --> YAML_HIS
    REC --> YAML_REC
    DRF --> YAML_DRF
    PRE --> YAML_PRE
    LOG --> LOG_F

    %% API error handling
    Q3C --> EXC
    LLM --> EXC
    OLL --> EXC
    ASR --> EXC

    %% Styling
    classDef entry fill:#6C63FF,stroke:#333,color:#fff
    classDef ui fill:#4ECDC4,stroke:#333,color:#000
    classDef core fill:#FFE66D,stroke:#333,color:#000
    classDef audio fill:#FF6B6B,stroke:#333,color:#fff
    classDef api fill:#A8DADC,stroke:#333,color:#000
    classDef script fill:#457B9D,stroke:#333,color:#fff
    classDef data fill:#E9C46A,stroke:#333,color:#000

    class main entry
    class MW,TT,CT,ET,AT,HT,ST,TH,WF ui
    class CFG,HIS,SSML,DUR,REC,I18N,LOG,CHN,PRE,DRF core
    class PLY,EXP,CAT audio
    class Q3C,LLM,OLL,ASR,EXC api
    class TTS_S,LLM_S,ASR_W,DL script
    class YAML_CFG,YAML_HIS,YAML_REC,YAML_DRF,YAML_PRE,LOG_F data
```

## 2. TTS Synthesis — Data Flow

```mermaid
sequenceDiagram
    participant U as 使用者
    participant TT as TextTab
    participant W as _TTSWorker
    participant Q3 as Qwen3Client
    participant S as tts_server.py
    participant P as AudioPlayer
    participant E as AudioExporter

    Note over U,E: 🎵 Text-to-Speech 合成流程

    U->>TT: 輸入文字 + 選預設
    TT->>TT: estimate_duration()
    TT-->>U: 顯示預估時長 MM:SS

    U->>TT: 點擊「合成」
    TT->>TT: add_recent(text)
    TT->>W: QThread.start()
    W->>Q3: synthesize(text, config)
    Q3->>S: POST /tts {text, speed, pitch}
    S->>S: model.synthesize()
    S-->>Q3: audio bytes (WAV)
    Q3-->>W: bytes
    W-->>TT: finished.emit(bytes)
    TT->>TT: WaveformWidget.set_audio()
    TT-->>U: 波形顯示 + 啟用播放

    U->>TT: 點擊「播放」
    TT->>P: play(audio_bytes)
    P-->>U: 🔊 音訊輸出

    U->>TT: 點擊「匯出」
    TT->>E: to_wav() / to_mp3()
    E-->>U: 💾 儲存檔案
```

## 3. Voice Clone — Data Flow

```mermaid
sequenceDiagram
    participant U as 使用者
    participant CT as CloneTab
    participant W as _CloneWorker
    participant Q3 as Qwen3Client
    participant S as tts_server.py

    Note over U,S: 🎤 Voice Clone 流程

    U->>CT: 選擇模式 (文字/音訊參考)
    U->>CT: 提供參考文字 or 上傳音訊檔

    U->>CT: 點擊「複製語音」
    CT->>W: QThread.start()

    alt 文字參考模式
        W->>Q3: clone_from_text(text, ref_text)
        Q3->>S: POST /clone/text
    else 音訊參考模式
        W->>Q3: clone_from_audio(text, ref_audio_b64)
        Q3->>S: POST /clone/audio
    end

    S->>S: model.clone()
    S-->>Q3: audio bytes
    Q3-->>W: bytes
    W-->>CT: finished.emit(bytes)
    CT-->>U: 播放 / 匯出
```

## 4. ASR Transcription — Data Flow

```mermaid
sequenceDiagram
    participant U as 使用者
    participant AT as ASRTab
    participant W as _ASRWorker
    participant AC as ASRClient
    participant AW as asr_worker.py

    Note over U,AW: 🗣️ Speech Recognition 流程

    U->>AT: 選擇音訊來源 (檔案/URL)
    U->>AT: 選語言 + 模型

    U->>AT: 點擊「辨識」
    AT->>W: QThread.start()
    W->>AC: transcribe(source, lang, model)

    alt Local 模式
        AC->>AW: subprocess stdin JSON
        AW->>AW: qwen3_asr.transcribe()
        AW-->>AC: stdout JSON result
    else API 模式
        AC->>AC: POST /v1/audio/transcriptions
    end

    AC-->>W: ASRResult
    W-->>AT: finished.emit(result)
    AT-->>U: 顯示文字 + 時間戳

    U->>AT: 匯出字幕
    AT->>AT: to_srt() / to_vtt() / to_txt()
    AT-->>U: 💾 儲存字幕檔
```

## 5. LLM Text Processing — Data Flow

```mermaid
sequenceDiagram
    participant U as 使用者
    participant ET as EditTab
    participant W as _EditWorker
    participant LLM as LLMClient
    participant S as llm_server.py

    Note over U,S: ✏️ 文字處理 / 翻譯流程

    U->>ET: 輸入文字 + 選模式
    U->>ET: 點擊「處理」
    ET->>W: QThread.start()

    alt 繁簡轉換 (OpenCC)
        W->>W: ChineseConverter.convert()
    else LLM 處理
        W->>LLM: polish() / translate() / custom()
        LLM->>S: POST /v1/chat/completions
        S-->>LLM: response text
    end

    LLM-->>W: processed text
    W-->>ET: finished.emit(text)
    ET-->>U: 顯示處理結果

    U->>ET: 「送至 TTS」
    ET-->>ET: text_sent.emit(text)
```

## 6. Module Dependency Matrix

| Module | Depends On | Depended By |
|--------|-----------|-------------|
| `config.py` | PyYAML | main.py, SettingsTab |
| `history.py` | PyYAML | main.py, TextTab, CloneTab, EditTab, HistoryTab |
| `ssml.py` | (stdlib) | TextTab |
| `duration_estimator.py` | (stdlib) | TextTab |
| `recent_texts.py` | PyYAML | TextTab |
| `i18n.py` | (stdlib) | (ready for UI integration) |
| `app_logger.py` | (stdlib) | MainWindow |
| `chinese_converter.py` | opencc | EditTab |
| `presets.py` | PyYAML | TextTab |
| `drafts.py` | PyYAML | TextTab |
| `player.py` | PySide6.QtMultimedia | TextTab, CloneTab |
| `exporter.py` | soundfile, pydub | TextTab, CloneTab |
| `concatenator.py` | soundfile, numpy | TextTab |
| `qwen3_client.py` | requests | TextTab, CloneTab |
| `llm_client.py` | requests | EditTab |
| `ollama_client.py` | requests | EditTab |
| `asr_client.py` | requests, subprocess | ASRTab |
| `theme.py` | PySide6 | MainWindow, all Tabs |

## 7. Layer Architecture Summary

```
┌─────────────────────────────────────────────────┐
│                  app/main.py                     │  Entry
├─────────────────────────────────────────────────┤
│  MainWindow │ TextTab │ CloneTab │ EditTab │ ... │  UI (PySide6)
├─────────────┼─────────┼──────────┼─────────┼─────┤
│  config │ history │ ssml │ i18n │ presets │ ...  │  Core
├─────────────┼─────────┼──────────┼─────────┼─────┤
│  player │ exporter │ concatenator                │  Audio
├─────────────┼─────────┼──────────────────────────┤
│  qwen3_client │ llm_client │ asr_client          │  API Clients
├─────────────┼─────────┼──────────────────────────┤
│  tts_server │ llm_server │ asr_worker            │  Scripts (FastAPI)
├─────────────┼─────────┼──────────────────────────┤
│  config.yaml │ data/*.yaml │ data/app.log        │  Persistence
└─────────────┴─────────┴──────────────────────────┘
```
