"""Tests for model_manager module."""

from app.core.model_manager import DEFAULT_MODELS, ModelInfo, get_gpu_info


class TestModelInfo:
    def test_default_models_exist(self):
        assert len(DEFAULT_MODELS) >= 3

    def test_model_info_fields(self):
        m = DEFAULT_MODELS[0]
        assert isinstance(m, ModelInfo)
        assert m.name
        assert m.repo_id
        assert m.dir_name
        assert m.group in ("tts", "asr", "llm")

    def test_model_info_is_frozen(self):
        m = DEFAULT_MODELS[0]
        try:
            m.name = "changed"
            raise AssertionError("Should have raised")
        except AttributeError:
            pass


class TestGetGpuInfo:
    def test_returns_string(self):
        result = get_gpu_info()
        assert isinstance(result, str)
        assert len(result) > 0
