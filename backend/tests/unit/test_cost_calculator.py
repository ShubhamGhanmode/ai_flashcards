"""Tests for model cost calculation helpers."""

from app.services.cost_calculator import CostCalculator


def test_estimate_cost_usd_for_known_model() -> None:
    cost = CostCalculator.estimate_cost_usd(
        model="gpt-5-nano",
        prompt_tokens=1_000_000,
        completion_tokens=500_000,
    )

    assert cost == 0.25


def test_unknown_model_uses_default_pricing() -> None:
    unknown_model_cost = CostCalculator.estimate_cost_usd(
        model="nonexistent-model",
        prompt_tokens=100_000,
        completion_tokens=100_000,
    )
    default_model_cost = CostCalculator.estimate_cost_usd(
        model=CostCalculator.DEFAULT_MODEL,
        prompt_tokens=100_000,
        completion_tokens=100_000,
    )

    assert unknown_model_cost == default_model_cost


def test_cost_to_cents_rounds_and_clamps() -> None:
    assert CostCalculator.cost_to_cents(0.251) == 25
    assert CostCalculator.cost_to_cents(0.255) == 26
    assert CostCalculator.cost_to_cents(-1.0) == 0
