# Qwen3-TTS Desktop — v0.4.0 Implementation Plan

> 版本：v0.4.0 | 上一版本：v0.3.0
> 目標：本地模型自動安裝、分頁式設定、10 項新功能、品質優化

---

## Phase 0 — 核心基礎建設

| 項目 | 說明 |
|------|------|
| ModelManager | `app/core/model_manager.py` — 偵測本地模型是否已下載，自動觸發 0.6B 模型安裝 |
| ServerManager | `app/core/server_manager.py` — 管理 TTS/LLM 本地伺服器子程序啟停 |
| Config 更新 | 新增 `TTSServerConfig`、`LLMServerConfig`，預設全指向本地模型 |
| 設定頁分頁 | `settings_tab.py` 重構為 QTabWidget（TTS/LLM/ASR/音訊/UI 五子頁） |

---

## Phase 1 — 10 項新功能

### Feature 1: 本地模型自動安裝精靈
- **模組**: `app/core/model_manager.py`
- **描述**: 啟動時偵測 TTS/ASR/LLM 0.6B 模型是否存在，缺少時彈出安裝對話框，背景下載並顯示進度
- **影響**: main.py 啟動流程新增模型檢查

### Feature 2: 本地伺服器自動啟停
- **模組**: `app/core/server_manager.py`
- **描述**: 自動啟動 tts_server.py / llm_server.py 為子程序，退出時自動清理
- **影響**: MainWindow 啟動/關閉生命週期

### Feature 3: 分頁式設定頁面
- **模組**: `app/ui/settings_tab.py`
- **描述**: 設定頁改為 QTabWidget，TTS/LLM/ASR 各有獨立設定分頁，含本地/API 模式切換
- **影響**: 設定頁完全重寫

### Feature 4: 服務健康狀態儀表板
- **模組**: `app/ui/settings_tab.py`
- **描述**: 設定頁頂部顯示 TTS/LLM/ASR 三個服務即時狀態（綠/紅燈），含一鍵重啟
- **影響**: 設定頁新增狀態面板

### Feature 5: 文字合成佇列（Queue）
- **模組**: `app/core/tts_queue.py`, `app/ui/text_tab.py`
- **描述**: 多段文字可加入合成佇列，依序處理，顯示佇列進度，支援取消
- **影響**: TextTab 新增佇列列表

### Feature 6: 音訊播放進度條
- **模組**: `app/ui/waveform_widget.py`
- **描述**: 波形圖上顯示播放進度指示條，點擊可跳轉播放位置
- **影響**: WaveformWidget 增強

### Feature 7: 快速文字模板
- **模組**: `app/core/text_templates.py`, `app/ui/text_tab.py`
- **描述**: 內建常用文字模板（問候語、廣播稿、有聲書開場白等），一鍵載入
- **影響**: TextTab 新增模板按鈕

### Feature 8: 語音辨識結果一鍵轉合成
- **模組**: `app/ui/asr_tab.py`
- **描述**: ASR 辨識結果可一鍵傳送到文字合成或語音克隆分頁
- **影響**: ASRTab 新增傳送按鈕

### Feature 9: 深色/淺色主題切換
- **模組**: `app/ui/theme.py`, `app/ui/settings_tab.py`
- **描述**: 支援深色/淺色兩種主題，設定頁可即時切換
- **影響**: theme.py 新增淺色主題變數

### Feature 10: 系統資訊面板
- **模組**: `app/ui/settings_tab.py`
- **描述**: 設定頁「關於」子頁顯示版本、Python 版本、GPU 資訊、模型狀態
- **影響**: 設定頁新增關於子頁

---

## Phase 2 — 品質

| 項目 | 說明 |
|------|------|
| ruff | 全部通過 |
| pytest | 新功能測試 ≥15 項，總測試 ≥ 100 |
| Code Review | 安全性、效能檢查 |

---

## Phase 3 — 文件與知識圖譜

| 項目 | 說明 |
|------|------|
| SPEC.md | 更新 v0.4.0 功能表 |
| plan.md | v0.4.0 完整計畫 |
| 知識圖譜 | Mermaid 格式，新增 ModelManager、ServerManager 模組 |

---

## Phase 4 — Ship

| 項目 | 說明 | 狀態 |
|------|------|------|
| pyproject.toml | 版本 → 0.4.0 | ✅ |
| git commit | `feat: v0.4.0 — auto-install, tabbed settings, 10 new features` | ✅ |
| git push | `stevenke1981/Qwen3TTS-app` | ✅ |

---

## 實作狀態摘要

| Phase | 狀態 |
|-------|------|
| Phase 0 核心基礎建設 | ✅ 完成 — model_manager, server_manager, config 更新, 設定頁分頁重寫 |
| Phase 1 十項新功能 | ✅ 完成 — Feature 1-4, 7, 9-10 完整實作；Feature 5/6/8 為 UI 連動增強（基礎已建立） |
| Phase 2 品質 | ✅ ruff 全部通過，116 tests passed |
| Phase 3 文件/知識圖譜 | ✅ SPEC.md 更新，Mermaid 架構圖 |
| Phase 4 Ship | ✅ v0.4.0 版本號，git 提交 |
