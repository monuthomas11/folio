from __future__ import annotations

import os

import httpx

from .base import LLMProvider, LLMProviderError

JSON_MODE_DISABLED = os.environ.get("OPENAI_JSON_MODE", "").lower() == "false"


class OpenAIProvider(LLMProvider):
    provider_id = "openai"

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model_name = model

    async def generate_text(
        self,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        json_mode: bool = True,
    ) -> str:
        payload: dict = {
            "model": self.model_name,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode and not JSON_MODE_DISABLED:
            payload["response_format"] = {"type": "json_object"}

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                res = await client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"OpenAI request failed: {exc}") from exc

        if res.status_code != 200:
            raise LLMProviderError(
                f"OpenAI HTTP {res.status_code}: {res.text[:500]}"
            )
        try:
            data = res.json()
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            raise LLMProviderError(f"Unexpected OpenAI response: {exc}") from exc
