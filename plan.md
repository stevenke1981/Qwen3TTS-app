# Qwen3-TTS Desktop — v0.3.0 Implementation Plan

> 版本：v0.3.0 | 上一版本：v0.2.0
> 目標：新增 10 項實用功能、移除 bat/sh 腳本、預設本地部署模型、建立知識圖譜

---

## Phase 0 — 清理與基礎

| 項目 | 說明 |
|------|------|
| 移除 bat/sh | 刪除 `start.bat`, `start.sh`, `setup-tts.bat`, `setup-tts.sh`, `setup_asr.bat`, `setup_asr.sh`, `setup_llm.bat`, `download_models.bat` |
| 更新 README | 改用 `python scripts/start.py` / `python scripts/setup.py` |
| 預設本地模型 | 所有 config 預設指向 localhost；settings 保留 API URL 可調 |

---

## Phase 1 — 10 項新功能

### Feature 1: SSML 標記編輯器
- **模組**: `app/core/ssml.py`, `app/ui/text_tab.py`
- **描述**: 提供 SSML 標記插入工具列（break/emphasis/prosody/phoneme），TTS 資深人員必備
- **影響**: TextTab 新增 SSML 工具列

### Feature 2: 音訊拼接器（Audio Concatenator）
- **模組**: `app/audio/concatenator.py`, `app/ui/text_tab.py`
- **描述**: 批次合成完成後可選擇將多段音檔拼接為單一 WAV/MP3，解決批次合成碎片問題
- **影響**: TextTab 批次合成後新增拼接按鈕

### Feature 3: 即時音訊長度預估
- **模組**: `app/core/duration_estimator.py`, `app/ui/text_tab.py`
- **描述**: 根據字數與語速參數即時預估合成時長（中文 ~3 字/秒, 英文 ~2.5 詞/秒），TTS 排程必備
- **影響**: TextTab 顯示預估時長

### Feature 4: 匯出格式選擇器
- **模組**: `app/ui/text_tab.py`, `app/ui/clone_tab.py`
- **描述**: 匯出時可選 WAV/MP3 格式，統一匯出流程
- **影響**: TextTab/CloneTab 匯出對話框加入格式選項

### Feature 5: 最近使用文字佇列
- **模組**: `app/core/recent_texts.py`, `app/ui/text_tab.py`
- **描述**: 記錄最近 20 筆合成文字，一鍵重新載入，避免重複輸入
- **影響**: TextTab 新增「最近文字」下拉

### Feature 6: 音訊比較播放器（A/B Compare）
- **模組**: `app/ui/text_tab.py`
- **描述**: 保留前一次與本次合成結果，可 A/B 切換比較，TTS 調參必備
- **影響**: TextTab 新增 A/B 切換

### Feature 7: 合成進度百分比
- **模組**: `app/ui/text_tab.py`, `app/ui/clone_tab.py`
- **描述**: 批次合成顯示 N/M 段落進度百分比，長文不再盲等
- **影響**: ProgressBar 顯示確定進度

### Feature 8: 多語言 UI 支援框架
- **模組**: `app/core/i18n.py`, 各 UI 檔案
- **描述**: 建立 i18n 字串表（zh-TW/en），所有 UI 文字走字串表，方便未來擴展
- **影響**: 全部 UI 文字集中管理

### Feature 9: 組態匯出/匯入
- **模組**: `app/ui/settings_tab.py`
- **描述**: 設定頁新增匯出/匯入設定 YAML，方便跨設備、團隊共享設定
- **影響**: SettingsTab 新增按鈕

### Feature 10: 應用程式日誌檢視器
- **模組**: `app/core/app_logger.py`, `app/ui/main_window.py`
- **描述**: 結構化 logging 到 `data/app.log`，主視窗新增「檢視日誌」動作（F12），方便排查問題
- **影響**: MainWindow 新增日誌面板

---

## Phase 2 — 品質

| 項目 | 說明 |
|------|------|
| ruff | 全部通過 |
| pytest | 新功能測試 ≥10 項，總測試 ≥ 60 |
| Code Review | 安全性、效能檢查 |

---

## Phase 3 — 文件與知識圖譜

| 項目 | 說明 |
|------|------|
| SPEC.md | 更新 v0.3.0 功能表 |
| 知識圖譜 | Mermaid 格式，含模組依賴、訊號流、資料流 |

---

## Phase 4 — Ship

| 項目 | 說明 |
|------|------|
| pyproject.toml | 版本 → 0.3.0 |
| git commit | `feat: v0.3.0 — 10 new features, cleanup, knowledge graph` |
| git push | `stevenke1981/Qwen3TTS-app` |
