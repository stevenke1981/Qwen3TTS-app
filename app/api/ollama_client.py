"""Ollama API Client for text editing and translation"""

import requests

from .exceptions import APIError


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")
        self.default_model = "llama3.2:latest"

    def generate(self, prompt: str, model: str | None = None) -> str:
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        model = model or self.default_model

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()
        except requests.exceptions.Timeout as exc:
            raise APIError("Ollama request timed out", status_code=408) from exc
        except requests.exceptions.RequestException as e:
            raise APIError(f"Ollama request failed: {e}") from e

    def polish(self, text: str, model: str | None = None) -> str:
        prompt = f"""請潤飾以下文字，使其更加通順、語法正確、語句優美。只需要輸出潤飾後的文字，不需要任何解釋。

原文：
{text}

潤飾後："""
        return self.generate(prompt, model)

    def translate(
        self,
        text: str,
        from_lang: str,
        to_lang: str,
        model: str | None = None,
    ) -> str:
        lang_names = {
            "zh": "中文",
            "en": "英文",
            "ja": "日文",
            "ko": "韓文",
            "fr": "法文",
            "de": "德文",
        }

        from_name = lang_names.get(from_lang, from_lang)
        to_name = lang_names.get(to_lang, to_lang)

        prompt = f"""請將以下文字從{from_name}翻譯成{to_name}。只需要輸出翻譯後的文字，不需要任何解釋或備註。

原文：
{text}

{to_name}翻譯："""
        return self.generate(prompt, model)

    def simplify_chinese(self, text: str, model: str | None = None) -> str:
        prompt = f"""請將以下繁體中文轉換為簡體中文。只需要輸出轉換後的文字，不需要任何解釋。

原文：
{text}

簡體中文："""
        return self.generate(prompt, model)

    def traditional_chinese(self, text: str, model: str | None = None) -> str:
        prompt = f"""請將以下簡體中文轉換為繁體中文。只需要輸出轉換後的文字，不需要任何解釋。

原文：
{text}

繁體中文："""
        return self.generate(prompt, model)

    def custom_process(
        self,
        text: str,
        instruction: str,
        model: str | None = None,
    ) -> str:
        prompt = f"""{instruction}

原文：
{text}

輸出："""
        return self.generate(prompt, model)

    def health_check(self) -> bool:
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def list_models(self) -> list[str]:
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except requests.exceptions.RequestException:
            return []
