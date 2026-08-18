import pytest

from app.services.llm.base import LLMProviderError, extract_json


def test_clean_json():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_fenced_json():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_prose_wrapped_json():
    text = "Here is the analysis:\n{" + '"rating": "HOLD"' + "}\nHope that helps."
    assert extract_json(text) == {"rating": "HOLD"}


def test_non_dict_json_rejected():
    with pytest.raises(LLMProviderError):
        extract_json("[1, 2, 3]")


def test_no_json_raises():
    with pytest.raises(LLMProviderError):
        extract_json("no json here at all")
