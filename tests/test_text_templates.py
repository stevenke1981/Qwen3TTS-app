"""Tests for text_templates module."""

import json

from app.core.text_templates import _DEFAULT_TEMPLATES, TemplateStore, TextTemplate


class TestTextTemplate:
    def test_defaults(self):
        t = TextTemplate(name="foo", text="bar")
        assert t.category == "自訂"

    def test_custom_category(self):
        t = TextTemplate(name="a", text="b", category="播報")
        assert t.category == "播報"


class TestTemplateStore:
    def test_load_creates_defaults(self, tmp_path):
        p = tmp_path / "tpl.json"
        store = TemplateStore.load(p)
        assert len(store.templates) == len(_DEFAULT_TEMPLATES)
        assert p.exists()

    def test_load_existing(self, tmp_path):
        p = tmp_path / "tpl.json"
        p.write_text(json.dumps([{"name": "x", "text": "y", "category": "z"}]), encoding="utf-8")
        store = TemplateStore.load(p)
        assert len(store.templates) == 1
        assert store.templates[0].name == "x"

    def test_add_and_remove(self, tmp_path):
        p = tmp_path / "tpl.json"
        store = TemplateStore.load(p)
        initial = len(store.templates)
        store.add("new", "hello")
        assert len(store.templates) == initial + 1
        store.remove(initial)
        assert len(store.templates) == initial

    def test_categories(self, tmp_path):
        p = tmp_path / "tpl.json"
        store = TemplateStore.load(p)
        cats = store.categories()
        assert isinstance(cats, list)
        assert len(cats) > 0

    def test_save_persist(self, tmp_path):
        p = tmp_path / "tpl.json"
        store = TemplateStore.load(p)
        store.add("persist", "data")
        store2 = TemplateStore.load(p)
        assert any(t.name == "persist" for t in store2.templates)

    def test_corrupt_file_uses_defaults(self, tmp_path):
        p = tmp_path / "tpl.json"
        p.write_text("NOT-JSON!!!", encoding="utf-8")
        store = TemplateStore.load(p)
        assert len(store.templates) == len(_DEFAULT_TEMPLATES)

    def test_remove_out_of_range(self, tmp_path):
        p = tmp_path / "tpl.json"
        store = TemplateStore.load(p)
        initial = len(store.templates)
        store.remove(999)
        assert len(store.templates) == initial
