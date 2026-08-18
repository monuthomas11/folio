from __future__ import annotations

import httpx

from .base import LLMProvider, LLMProviderError

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(LLMProvider):
    provider_id = "gemini"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model_name = model

    async def generate_text(
        self,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{system}\n\n{user}"}],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }
        url = f"{BASE_URL}/{self.model_name}:generateContent?key={self.api_key}"
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                res = await client.post(url, json=payload)
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Gemini request failed: {exc}") from exc

        if res.status_code != 200:
            raise LLMProviderError(
                f"Gemini HTTP {res.status_code}: {res.text[:500]}"
            )
        try:
            data = res.json()
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(part.get("text", "") for part in parts)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMProviderError(f"Unexpected Gemini response: {exc}") from exc
