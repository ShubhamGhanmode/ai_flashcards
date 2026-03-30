"""Shared helpers for extracting and combining token usage metadata."""

import json
from typing import Any


def usage_from_raw_message(raw_message: Any) -> tuple[int, int, int]:
    """Extract prompt/completion/total token counts from a raw LLM message."""
    usage = getattr(raw_message, "usage_metadata", None) or {}
    prompt = int(usage.get("input_tokens", 0))
    completion = int(usage.get("output_tokens", 0))
    total = int(usage.get("total_tokens", 0))
    return prompt, completion, total


def combine_usage_counts(
    first_prompt: int,
    first_completion: int,
    first_total: int,
    second_prompt: int,
    second_completion: int,
    second_total: int,
) -> tuple[int, int, int]:
    """Add two token-usage tuples."""
    return (
        first_prompt + second_prompt,
        first_completion + second_completion,
        first_total + second_total,
    )


def as_text(value: Any, max_chars: int = 1600) -> str:
    """Convert unknown payloads to safely truncated text for logging/details."""
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=True)
        except TypeError:
            text = str(value)
    return text[:max_chars]

