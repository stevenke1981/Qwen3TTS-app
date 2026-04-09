# Graph Report - app  (2026-04-09)

## Corpus Check
- Corpus is ~19,787 words - fits in a single context window. You may not need a graph.

## Summary
- 592 nodes · 1112 edges · 24 communities detected
- Extraction: 54% EXTRACTED · 46% INFERRED · 0% AMBIGUOUS · INFERRED: 510 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `TextTab` - 50 edges
2. `ASRTab` - 46 edges
3. `SettingsTab` - 40 edges
4. `MainWindow` - 36 edges
5. `HistoryTab` - 32 edges
6. `CloneTab` - 31 edges
7. `EditTab` - 31 edges
8. `LLMClient` - 30 edges
9. `HistoryEntry` - 24 edges
10. `ErrorConsoleWidget` - 24 edges

## Surprising Connections (you probably didn't know these)
- `History management tab` --uses--> `HistoryEntry`  [INFERRED]
  app\ui\history_tab.py → app\core\history.py
- `Export currently filtered history to a CSV file.` --uses--> `HistoryEntry`  [INFERRED]
  app\ui\history_tab.py → app\core\history.py
- `Qwen3-TTS Desktop Application - Entry Point` --uses--> `ASRClient`  [INFERRED]
  app\main.py → app\api\asr_client.py
- `Qwen3-TTS Desktop Application - Entry Point` --uses--> `LLMClient`  [INFERRED]
  app\main.py → app\api\llm_client.py
- `Qwen3-TTS Desktop Application - Entry Point` --uses--> `Qwen3Client`  [INFERRED]
  app\main.py → app\api\qwen3_client.py

## Communities

### Community 0 - "Voice Clone UI Tab"
Cohesion: 0.04
Nodes (17): CloneTab, EditTab, HistoryTab, Export currently filtered history to a CSV file., MainWindow, Restore window size and position from QSettings., Create system tray icon with context menu., Save geometry; minimize to tray if active, otherwise quit. (+9 more)

### Community 1 - "Audio Workers & Playback"
Cohesion: 0.05
Nodes (24): _CloneWorker, Voice clone tab with text and audio reference support, Background worker for voice cloning., AudioExporter, HistoryEntry, AudioPlayer, VoicePreset, QDialog (+16 more)

### Community 2 - "Speech Recognition (ASR)"
Cohesion: 0.05
Nodes (33): ASRClient, ASRResult, ASRSegment, _fmt_srt(), _fmt_vtt(), ASR Client — bridges the main `venv` and the `venv-asr` interpreter.
 
 The main, Format seconds as VTT timestamp ``HH:MM:SS.mmm``., Map a raw ``PROGRESS:`` stage string to a human-readable Chinese label. (+25 more)

### Community 3 - "LLM Integration Layer"
Cohesion: 0.05
Nodes (23): Exception, LLMClient, LLMError, Unified multi-provider LLM client for 潤稿 / translate functions.
 
 Supported pro, Generate a response for the given prompt (public alias)., Return *True* when the server is reachable., Return a list of available model names from the provider., Raised when an LLM API call fails. (+15 more)

### Community 4 - "App Entry & Config Loading"
Cohesion: 0.06
Nodes (28): Config, Top-level application configuration., _dir_size(), main(), _prompt_and_download(), Qwen3-TTS Desktop Application - Entry Point, Ask the user whether to download missing models, then start if yes., Return total bytes of all files under *path* (returns 0 if not found). (+20 more)

### Community 5 - "UI Tab Layout"
Cohesion: 0.08
Nodes (20): Edit & Translate tab with multi-provider LLM integration, Audio export utilities, History management tab, Qwen3-TTS Desktop Application, Main application window, Audio playback using QSound, Settings tab — tabbed layout with TTS / LLM / ASR / Audio / About sub-pages., _apply_light_overrides() (+12 more)

### Community 6 - "API Clients & Exceptions"
Cohesion: 0.15
Nodes (12): APIError, API client exceptions, Exception raised when voice cloning fails, Exception raised when TTS synthesis fails, Base exception for API errors, TTSError, VoiceCloneError, Ollama API Client for text editing and translation (+4 more)

### Community 7 - "Chinese Text Conversion"
Cohesion: 0.22
Nodes (12): ChineseConverter, hk2s(), Chinese Simplified/Traditional conversion utilities, s2hk(), s2t(), s2tw(), t2s(), tw2s() (+4 more)

### Community 8 - "Error Console UI"
Cohesion: 0.15
Nodes (8): ErrorConsoleHandler, ErrorConsoleWidget, _get_emitter(), Error Console Widget — persistent panel showing WARNING/ERROR log messages.
 
 I, Create and return a logging handler that feeds into this widget., logging.Handler that forwards records to ErrorConsoleWidget via Qt signals., Persistent log panel showing WARNING / ERROR messages with copy support., _SignalEmitter

### Community 9 - "Model Management"
Cohesion: 0.17
Nodes (9): download_models_sync(), _fmt_size(), get_missing_models(), is_model_downloaded(), ModelDownloadWorker, ModelInfo, Model manager — detect, download, and manage local Qwen3 models.  Worker ↔ UI co, Download models in a background QThread.      All progress is communicated via ` (+1 more)

### Community 10 - "Configuration Schema"
Cohesion: 0.18
Nodes (17): APIConfig, ASRConfig, ASRServerConfig, AudioConfig, _from_dict(), from_yaml(), HistoryConfig, LLMConfig (+9 more)

### Community 11 - "SSML Speech Markup"
Cohesion: 0.12
Nodes (15): SSML (Speech Synthesis Markup Language) tag helpers for TTS text.
 
 Provides fu, Represents an SSML tag that can be inserted into text., Return a <break> tag with the given duration in milliseconds., Wrap *text* in an <emphasis> tag., Wrap *text* in a <prosody> tag for rate/pitch control., Wrap *text* with an IPA phoneme annotation., Wrap the full body in a complete SSML <speak> document., Remove all XML/SSML tags, returning plain text. (+7 more)

### Community 12 - "History Management"
Cohesion: 0.22
Nodes (4): from_dict(), HistoryManager, History management for TTS operations, Delete a single entry by ID. Returns True if found and deleted.

### Community 13 - "Internationalisation (i18n)"
Cohesion: 0.2
Nodes (9): available_locales(), get_locale(), Minimal i18n string table for the application UI.
 
 Usage::
 
     from app.cor, Switch the active locale (e.g. ``'zh-TW'`` or ``'en'``)., Return the current active locale., Return all registered locale codes., Translate *key* to the active locale.
 
     Supports ``str.format()`` interpola, set_locale() (+1 more)

### Community 14 - "Text Templates"
Cohesion: 0.31
Nodes (5): load(), Reusable text templates for TTS synthesis., Manage user text templates on disk (JSON)., TemplateStore, TextTemplate

### Community 15 - "Logging System"
Cohesion: 0.28
Nodes (8): _ensure_init(), get_logger(), log_path(), Structured application logger with file rotation.
 
 Provides :func:`get_logger`, Return a child logger under the ``app`` namespace.
 
     >>> log = get_logger(", Return the last *lines* lines from the log file., Return the absolute path of the log file., read_log_tail()

### Community 16 - "Duration Estimator"
Cohesion: 0.28
Nodes (8): _count_cjk(), _count_words(), estimate_duration(), format_duration(), Estimate audio duration from text length and synthesis parameters.
 
 Heuristic, Count non-CJK words (split by whitespace)., Return estimated duration in seconds.
 
     Parameters
     ----------
     tex, Format seconds into a human-readable string like '1:23' or '0:05'.

### Community 17 - "Voice Presets"
Cohesion: 0.25
Nodes (8): delete_custom_preset(), from_dict(), load_presets(), Voice preset profiles — save/load speed, pitch, volume combinations., Load presets from disk, merging with built-ins., Append a custom preset to disk., Remove a custom preset by name., save_custom_preset()

### Community 18 - "Recent Texts"
Cohesion: 0.28
Nodes (8): add_recent(), clear_recent(), load_recent(), Recent synthesis texts — quick-reload queue for repeated TTS tasks., Load recent texts from disk (newest first)., Add *text* to the recent queue and persist.
 
     - Deduplicates (moves existin, Remove all recent texts., _save()

### Community 19 - "Audio Concatenation"
Cohesion: 0.4
Nodes (5): concatenate_audio(), concatenate_to_file(), Audio concatenation — join multiple WAV byte chunks into a single file., Concatenate multiple WAV byte blobs into a single WAV.
 
     Parameters
     --, Concatenate and write to a file.
 
     Returns the Path written.

### Community 20 - "Auto Punctuation"
Cohesion: 0.4
Nodes (5): add_punctuation(), _is_question(), Auto-punctuation post-processing for ASR transcripts.
 
 Inserts basic Chinese s, Heuristic: does this segment look like a question?, Add basic Chinese punctuation to a raw ASR transcript.
 
     Parameters
     --

### Community 21 - "Draft Auto-Save"
Cohesion: 0.33
Nodes (5): load_drafts(), Auto-save draft text across sessions., Save draft texts to disk. Keys: 'text_tab', 'clone_tab', 'clone_ref', 'edit_tab', Load draft texts from disk., save_drafts()

### Community 22 - "ASR Venv Path"
Cohesion: 1.0
Nodes (1): Path to the venv-asr Python interpreter.

### Community 23 - "MP3 Export Helper"
Cohesion: 1.0
Nodes (1): 將音訊匯出為 MP3（需要安裝 pydub 與 ffmpeg）。

## Knowledge Gaps
- **111 isolated node(s):** `Qwen3-TTS Desktop Application`, `ASR Client — bridges the main `venv` and the `venv-asr` interpreter.
 
 The main`, `One subtitle/timestamp segment.`, `Full transcription result returned by :meth:`ASRClient.transcribe`.`, `Export segments as SRT subtitle text.` (+106 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `ASR Venv Path`** (1 nodes): `Path to the venv-asr Python interpreter.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `MP3 Export Helper`** (1 nodes): `將音訊匯出為 MP3（需要安裝 pydub 與 ffmpeg）。`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TextTab` connect `Audio Workers & Playback` to `Voice Clone UI Tab`, `LLM Integration Layer`, `UI Tab Layout`?**
  _High betweenness centrality (0.144) - this node is a cross-community bridge._
- **Why does `MainWindow` connect `Voice Clone UI Tab` to `Audio Workers & Playback`, `Speech Recognition (ASR)`, `LLM Integration Layer`, `App Entry & Config Loading`, `UI Tab Layout`, `Error Console UI`?**
  _High betweenness centrality (0.141) - this node is a cross-community bridge._
- **Why does `ASRTab` connect `Speech Recognition (ASR)` to `Voice Clone UI Tab`, `LLM Integration Layer`, `UI Tab Layout`?**
  _High betweenness centrality (0.127) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `TextTab` (e.g. with `_StatusDot` and `MainWindow`) actually correct?**
  _`TextTab` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `ASRTab` (e.g. with `ASRClient` and `ASRResult`) actually correct?**
  _`ASRTab` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `SettingsTab` (e.g. with `_StatusDot` and `MainWindow`) actually correct?**
  _`SettingsTab` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `MainWindow` (e.g. with `Qwen3-TTS Desktop Application - Entry Point` and `Return total bytes of all files under *path* (returns 0 if not found).`) actually correct?**
  _`MainWindow` has 11 INFERRED edges - model-reasoned connections that need verification._
---

## Update — 2026-04-10: 語音模版功能 (50+ Templates)

### Changes Applied
- **`app/core/text_templates.py`** — `_DEFAULT_TEMPLATES` expanded from 6 → **56 templates** across **9 categories**
- **`app/ui/text_tab.py`** — Added `語音模版` GroupBox with cascading category + template dropdowns,
  apply & save-as-template actions. New methods: `_load_template_categories`, `_on_tpl_category_changed`,
  `_on_apply_template`, `_on_save_as_template`.

### New Nodes Added (+9)
| ID | Description |
|----|-------------|
| `TemplateStore` | Manages 56 TTS templates across 9 categories |
| `TextTemplate` | Dataclass for a single template entry |
| `_DEFAULT_TEMPLATES` | 56 built-in templates: 播報 商業 教育 故事朗讀 廣告行銷 客服 社群媒體 提醒公告 娛樂 |
| `_load_template_categories()` | Populates category dropdown |
| `_on_tpl_category_changed()` | Filters templates by category |
| `_on_apply_template()` | Inserts template into text input |
| `_on_save_as_template()` | Saves custom template |
| `tpl_category_combo` | Category QComboBox widget |
| `tpl_name_combo` | Template name QComboBox widget |

### Template Category Breakdown
| Category | Templates |
|----------|-----------|
| 播報 | 8 |
| 商業 | 8 |
| 教育 | 7 |
| 故事朗讀 | 7 |
| 廣告行銷 | 6 |
| 客服 | 6 |
| 社群媒體 | 5 |
| 提醒公告 | 5 |
| 娛樂 | 4 |
| **Total** | **56** |
