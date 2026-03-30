"""Model pricing and cost conversion helpers."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    """Per-million-token pricing in USD."""

    input_per_million: float
    output_per_million: float


class CostCalculator:
    """Compute API costs from token usage."""

    DEFAULT_MODEL = "gpt-5-nano"
    PRICING_BY_MODEL: dict[str, ModelPricing] = {
        "gpt-5-nano": ModelPricing(input_per_million=0.05, output_per_million=0.40),
        "gpt-5-mini": ModelPricing(input_per_million=0.25, output_per_million=2.00),
        "gpt-4o-mini": ModelPricing(input_per_million=0.15, output_per_million=0.60),
    }

    @classmethod
    def pricing_for_model(cls, model: str) -> ModelPricing:
        """Return model pricing, falling back to the default model table."""
        return cls.PRICING_BY_MODEL.get(
            model,
            cls.PRICING_BY_MODEL[cls.DEFAULT_MODEL],
        )

    @classmethod
    def estimate_cost_usd(
        cls,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Estimate request cost in USD from token counts."""
        pricing = cls.pricing_for_model(model)
        prompt_cost = (max(prompt_tokens, 0) / 1_000_000) * pricing.input_per_million
        completion_cost = (
            max(completion_tokens, 0) / 1_000_000
        ) * pricing.output_per_million
        return prompt_cost + completion_cost

    @staticmethod
    def cost_to_cents(cost_usd: float) -> int:
        """Convert USD to integer cents for persistence."""
        return max(0, int(round(cost_usd * 100)))
