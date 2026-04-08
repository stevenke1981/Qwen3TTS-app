"""Reusable text templates for TTS synthesis."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

_DEFAULT_TEMPLATES: list[dict] = [
    {
        "name": "新聞播報",
        "text": "各位觀眾朋友大家好，以下是今天的重要新聞。",
        "category": "播報",
    },
    {
        "name": "天氣預報",
        "text": "今天天氣晴，氣溫介於攝氏二十五度到三十度之間，風力較弱。",
        "category": "播報",
    },
    {
        "name": "歡迎詞",
        "text": "歡迎來到我們的頻道，今天我們要分享的主題是。",
        "category": "開場",
    },
    {
        "name": "影片結尾",
        "text": "感謝收看，如果喜歡的話請幫我們按讚訂閱，我們下次見！",
        "category": "結尾",
    },
    {
        "name": "產品介紹",
        "text": "這款產品的最大特色是高品質與出色的使用體驗。",
        "category": "商業",
    },
    {
        "name": "有聲書段落",
        "text": "在那個寧靜的下午，她走進了那間充滿書香的小店。",
        "category": "朗讀",
    },
]


@dataclass
class TextTemplate:
    name: str
    text: str
    category: str = "自訂"


@dataclass
class TemplateStore:
    """Manage user text templates on disk (JSON)."""

    templates: list[TextTemplate] = field(default_factory=list)
    _path: Path | None = field(default=None, repr=False)

    @classmethod
    def load(cls, path: Path) -> TemplateStore:
        store = cls(_path=path)
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                store.templates = [TextTemplate(**item) for item in raw]
            except Exception:
                log.warning("無法讀取模板檔案 %s，使用預設模板", path)
                store.templates = [TextTemplate(**d) for d in _DEFAULT_TEMPLATES]
        else:
            store.templates = [TextTemplate(**d) for d in _DEFAULT_TEMPLATES]
            store.save()
        return store

    def save(self) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(t) for t in self.templates]
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, name: str, text: str, category: str = "自訂") -> TextTemplate:
        tpl = TextTemplate(name=name, text=text, category=category)
        self.templates.append(tpl)
        self.save()
        return tpl

    def remove(self, index: int) -> None:
        if 0 <= index < len(self.templates):
            self.templates.pop(index)
            self.save()

    def categories(self) -> list[str]:
        return sorted({t.category for t in self.templates})
