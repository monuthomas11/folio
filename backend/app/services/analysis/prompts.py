from __future__ import annotations

import json
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
PROMPT_VERSION = "v1"

_PROMPT_FILES = {
    "fundamental": "fundamental_analyst_v1.md",
    "technical": "technical_analyst_v1.md",
    "portfolio": "portfolio_analyst_v1.md",
    "committee": "final_investment_committee_v1.md",
}

_cache: dict[str, str] = {}

SYSTEM_PROMPT = (
    "You are a disciplined equity/portfolio analyst for Indian listed "
    "(NSE/BSE) securities. You reason only from provided evidence and always "
    "respond with a single JSON object matching the schema in the prompt. "
    "Never output markdown or prose outside the JSON."
)


def load_prompt(agent: str) -> str:
    if agent in _cache:
        return _cache[agent]
    filename = _PROMPT_FILES[agent]
    text = (PROMPTS_DIR / filename).read_text(encoding="utf-8")
    _cache[agent] = text
    return text


def render_agent_prompt(
    agent: str,
    evidence_pack: dict,
    extra: dict | None = None,
) -> str:
    payload: dict = {}
    if extra:
        payload.update(extra)
    prompt = {
        "evidence_pack": evidence_pack,
        **payload,
    }
    return load_prompt(agent) + "\n\nEVIDENCE:\n" + json.dumps(
        prompt, indent=2, default=str
    )


def get_system_prompt() -> str:
    return SYSTEM_PROMPT
