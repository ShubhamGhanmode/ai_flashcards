"""Token estimation utilities for non-generative cost previews."""

from dataclasses import dataclass

import tiktoken

MODEL_ENCODING_FALLBACK = "o200k_base"

# Token overhead for chat wrapper + structured-output schema envelope.
CHAT_MESSAGE_OVERHEAD_TOKENS = 18
STRUCTURED_OUTPUT_OVERHEAD_TOKENS = 240

# Conservative completion estimate for deck schema output.
BASE_COMPLETION_TOKENS = 90
COMPLETION_TOKENS_PER_CONCEPT = 115


@dataclass(frozen=True)
class TokenEstimate:
    """Estimated token usage split for one generation request."""

    prompt: int
    completion: int

    @property
    def total(self) -> int:
        """Return total estimated tokens."""
        return self.prompt + self.completion

    def as_dict(self) -> dict[str, int]:
        """Serialize estimate as a plain dict."""
        return {
            "prompt": self.prompt,
            "completion": self.completion,
            "total": self.total,
        }


class TokenEstimator:
    """Estimate token usage for deck generation requests."""

    def __init__(self, model: str) -> None:
        self.model = model
        self._encoding = self._resolve_encoding(model)

    @staticmethod
    def _resolve_encoding(model: str) -> tiktoken.Encoding:
        """Resolve model encoding with a deterministic fallback."""
        try:
            return tiktoken.encoding_for_model(model)
        except KeyError:
            return tiktoken.get_encoding(MODEL_ENCODING_FALLBACK)

    def count_tokens(self, text: str) -> int:
        """Count tokens in plain text."""
        if not text:
            return 0
        return len(self._encoding.encode(text))

    def estimate_deck_request(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_concepts: int,
    ) -> dict[str, int]:
        """Estimate prompt/completion/total tokens for deck generation."""
        prompt_tokens = (
            self.count_tokens(system_prompt)
            + self.count_tokens(user_prompt)
            + CHAT_MESSAGE_OVERHEAD_TOKENS
            + STRUCTURED_OUTPUT_OVERHEAD_TOKENS
        )
        completion_tokens = (
            BASE_COMPLETION_TOKENS
            + (max_concepts * COMPLETION_TOKENS_PER_CONCEPT)
        )
        return TokenEstimate(
            prompt=prompt_tokens,
            completion=completion_tokens,
        ).as_dict()
