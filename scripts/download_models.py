"""下載 Qwen3 模型到專案的 models/ 目錄。

用法（在 venv-asr / venv-llm 環境下執行）:
    python scripts/download_models.py           # 互動式選單
    python scripts/download_models.py --all     # 下載全部模型
    python scripts/download_models.py --ids 1,3 # 下載指定模型
    python scripts/download_models.py --group asr
    python scripts/download_models.py --group tts
    python scripts/download_models.py --group llm
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ─── 模型清單 ──────────────────────────────────────────────────────────────────

MODELS: list[dict] = [
    # ── ASR ──────────────────────────────────────────────────────────────────
    {
        "id":    1,
        "group": "asr",
        "repo_id": "Qwen/Qwen3-ASR-0.6B",
        "name":  "Qwen3-ASR-0.6B",
        "desc":  "語音辨識（快速，~1.2 GB）",
        "dir":   "Qwen3-ASR-0.6B",
    },
    {
        "id":    2,
        "group": "asr",
        "repo_id": "Qwen/Qwen3-ASR-1.7B",
        "name":  "Qwen3-ASR-1.7B",
        "desc":  "語音辨識（精確，~3.4 GB）",
        "dir":   "Qwen3-ASR-1.7B",
    },
    {
        "id":    3,
        "group": "asr",
        "repo_id": "Qwen/Qwen3-ForcedAligner-0.6B",
        "name":  "Qwen3-ForcedAligner-0.6B",
        "desc":  "時間軸對齊（ASR 時間戳記必備，~0.5 GB）",
        "dir":   "Qwen3-ForcedAligner-0.6B",
    },
    # ── TTS ──────────────────────────────────────────────────────────────────
    {
        "id":    4,
        "group": "tts",
        "repo_id": "Qwen/Qwen3-TTS-0.6B",
        "name":  "Qwen3-TTS-0.6B",
        "desc":  "語音合成（~1.2 GB）",
        "dir":   "Qwen3-TTS-0.6B",
    },
    {
        "id":    5,
        "group": "tts",
        "repo_id": "Qwen/Qwen3-TTS-1.7B",
        "name":  "Qwen3-TTS-1.7B",
        "desc":  "語音合成（高品質，~3.4 GB）",
        "dir":   "Qwen3-TTS-1.7B",
    },
    # ── LLM（潤稿翻譯）─────────────────────────────────────────────────────
    {
        "id":    6,
        "group": "llm",
        "repo_id": "Qwen/Qwen3-0.6B",
        "name":  "Qwen3-0.6B",
        "desc":  "LLM 潤稿翻譯（超小，~1.2 GB）",
        "dir":   "Qwen3-0.6B",
    },
    {
        "id":    7,
        "group": "llm",
        "repo_id": "Qwen/Qwen3-1.7B",
        "name":  "Qwen3-1.7B",
        "desc":  "LLM 潤稿翻譯（小型，~3.4 GB）",
        "dir":   "Qwen3-1.7B",
    },
    {
        "id":    8,
        "group": "llm",
        "repo_id": "Qwen/Qwen3-4B",
        "name":  "Qwen3-4B",
        "desc":  "LLM 潤稿翻譯（中型，~8 GB）",
        "dir":   "Qwen3-4B",
    },
]

# ─── 路徑 ─────────────────────────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_MODELS_DIR   = _PROJECT_ROOT / "models"


def _local_path(model_dir: str) -> Path:
    return _MODELS_DIR / model_dir


def _is_downloaded(model_dir: str) -> bool:
    """Model is considered downloaded if config.json exists in the local dir."""
    return (_local_path(model_dir) / "config.json").exists()


# ─── Download ─────────────────────────────────────────────────────────────────

def download_model(model: dict) -> None:
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("[ERROR] huggingface_hub 未安裝。請先執行 pip install huggingface_hub")
        sys.exit(1)

    local_dir = _local_path(model["dir"])
    local_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n--- Downloading {model['repo_id']} ---")
    print(f"    目標目錄: {local_dir}")
    print("    (large file; progress is shown below)")

    snapshot_download(
        repo_id=model["repo_id"],
        local_dir=str(local_dir),
        ignore_patterns=["*.msgpack", "flax_model*", "tf_model*", "rust_model*"],
    )

    print(f"Download complete: {local_dir}")


# ─── UI ───────────────────────────────────────────────────────────────────────

_GROUP_LABELS = {"asr": "ASR 語音辨識", "tts": "TTS 語音合成", "llm": "LLM 潤稿翻譯"}


def print_menu() -> None:
    print("\n可下載的模型（儲存至 models/ 目錄）：")
    current_group = ""
    for m in MODELS:
        if m["group"] != current_group:
            current_group = m["group"]
            print(f"\n  ── {_GROUP_LABELS[current_group]} ──")
        status = "✓ 已下載" if _is_downloaded(m["dir"]) else "  未下載"
        print(f"  {m['id']}. [{status}] {m['name']:<34} {m['desc']}")
    print()
    print("  all          下載全部模型")
    print("  --group asr  只下載 ASR 相關模型")
    print("  --group tts  只下載 TTS 相關模型")
    print("  --group llm  只下載 LLM 潤稿翻譯模型")
    print()


def parse_selection(raw: str) -> list[dict]:
    raw = raw.strip().lower()
    if raw == "all":
        return MODELS
    id_map = {m["id"]: m for m in MODELS}
    selected = []
    for token in raw.replace(" ", "").split(","):
        try:
            n = int(token)
            if n in id_map:
                selected.append(id_map[n])
            else:
                print(f"[WARN] 無效編號 {n}，跳過。")
        except ValueError:
            print(f"[WARN] 無法解析 '{token}'，跳過。")
    return selected


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="下載 Qwen3 模型到 models/ 目錄")
    parser.add_argument("--all",   action="store_true", help="下載全部模型")
    parser.add_argument("--ids",   type=str, default="", help="逗號分隔的模型編號，例如 1,3")
    parser.add_argument("--group", type=str, default="", choices=["asr", "tts", "llm"],
                        help="只下載指定群組")
    args = parser.parse_args()

    _MODELS_DIR.mkdir(exist_ok=True)

    if args.all:
        targets = MODELS
    elif args.group:
        targets = [m for m in MODELS if m["group"] == args.group]
    elif args.ids:
        targets = parse_selection(args.ids)
    else:
        print_menu()
        ids_str = list(range(1, len(MODELS) + 1))
        raw = input(f"Select model to download [{'/'.join(str(i) for i in ids_str)}/all]: ").strip()
        targets = parse_selection(raw)

    if not targets:
        print("[INFO] 未選擇任何模型。")
        return

    for model in targets:
        if _is_downloaded(model["dir"]):
            print(f"[INFO] {model['name']} 已存在於 {_local_path(model['dir'])}，跳過。")
            continue
        download_model(model)

    print("\n✓ 完成！所有選取的模型已儲存至：")
    print(f"   {_MODELS_DIR}")


if __name__ == "__main__":
    main()
