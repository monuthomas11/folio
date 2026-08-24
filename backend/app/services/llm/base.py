from __future__ import annotations

import asyncio
import json
import re
from abc import ABC, abstractmethod
from typing import Any

from .rate_limiter import get_llm_rate_limiter


class LLMProviderError(Exception):
    pass


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_TRANSIENT_STATUSES = {429, 500, 502, 503, 504}


def _is_transient_error(exc: LLMProviderError) -> bool:
    text = str(exc)
    match = re.search(r"HTTP (\d{3})", text)
    if match and int(match.group(1)) in _TRANSIENT_STATUSES:
        return True
    return bool(re.search(r"request failed", text, re.IGNORECASE))


def _retry_delay(attempt: int) -> float:
    return 3.0 * (2 ** attempt)


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
                if self.provider_id != "mock":
                    await get_llm_rate_limiter().acquire()
                raw = await self.generate_text(
                    system=system,
                    user=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=True,
                )
                return extract_json(raw)
            except LLMProviderError as exc:
                if _is_transient_error(exc):
                    last_error = exc
                    await asyncio.sleep(_retry_delay(attempt))
                    continue
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
        json_mode: bool = True,
    ) -> str:
        raise NotImplementedError
