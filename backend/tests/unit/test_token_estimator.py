"""Tests for token estimation utility."""

import tiktoken

from app.services.token_estimator import TokenEstimator


def test_count_tokens_is_deterministic() -> None:
    estimator = TokenEstimator(model="gpt-5-nano")

    first = estimator.count_tokens("Binary Search Trees")
    second = estimator.count_tokens("Binary Search Trees")

    assert first > 0
    assert first == second


def test_estimate_deck_request_scales_with_concepts() -> None:
    estimator = TokenEstimator(model="gpt-5-nano")

    low = estimator.estimate_deck_request(
        system_prompt="system",
        user_prompt="user",
        max_concepts=3,
    )
    high = estimator.estimate_deck_request(
        system_prompt="system",
        user_prompt="user",
        max_concepts=7,
    )

    assert low["total"] == low["prompt"] + low["completion"]
    assert high["completion"] > low["completion"]
    assert high["total"] > low["total"]


def test_falls_back_to_o200k_base_for_unknown_model(monkeypatch) -> None:
    original_get_encoding = tiktoken.get_encoding
    monkeypatch.setattr(tiktoken, "encoding_for_model", lambda _model: (_ for _ in ()).throw(KeyError("unknown")))
    fallback_encoding = original_get_encoding("o200k_base")
    monkeypatch.setattr(
        tiktoken,
        "get_encoding",
        lambda name: fallback_encoding if name == "o200k_base" else original_get_encoding(name),
    )

    estimator = TokenEstimator(model="unknown-model")

    assert estimator.count_tokens("fallback works") > 0
