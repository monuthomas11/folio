from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any


class LLMProviderError(Exception):
    pass


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    try:
        data = json.loads(stripped)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, ValueError):
        pass

    for match in _FENCE_RE.findall(text):
        candidate = match.strip()
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, ValueError):
            continue

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, ValueError):
            pass

    raise LLMProviderError("No JSON object found in model response")


class LLMProvider(ABC):
    provider_id: str = "base"
    model_name: str = ""

    async def generate_json(
        self,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        user_prompt = user
        for attempt in range(3):
            try:
                raw = await self.generate_text(
                    system=system,
                    user=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return extract_json(raw)
            except LLMProviderError as exc:
                if "HTTP" in str(exc) or "request" in str(exc).lower():
                    raise
                last_error = exc
            except Exception as exc:
                last_error = exc
            user_prompt = (
                user_prompt
                + "\n\nYour previous response could not be parsed as JSON. "
                "Respond with JSON only. No prose, no markdown fences."
            )
        raise LLMProviderError(f"Failed to obtain valid JSON: {last_error}")

    @abstractmethod
    async def generate_text(
        self,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        raise NotImplementedError
