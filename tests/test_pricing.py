"""Tests for burnmap.pricing — rate lookup and billing labels."""
import datetime

import pytest

from burnmap.pricing import (
    LABEL_REAL,
    LABEL_SYNTHETIC,
    billing_label,
    compute_cost,
    lookup_rates,
)


class TestLookupRates:
    def test_known_model_returns_rates(self):
        rates = lookup_rates("claude-3-5-sonnet-20241022", "2024-11-01")
        assert rates["input_per_1m"] == pytest.approx(3.0)
        assert rates["output_per_1m"] == pytest.approx(15.0)
        assert rates["cached_per_1m"] == pytest.approx(0.3)

    def test_unknown_model_returns_fallback(self):
        rates = lookup_rates("totally-made-up-model-9000", "2024-01-01")
        assert "input_per_1m" in rates
        assert "output_per_1m" in rates
        assert "cached_per_1m" in rates

    def test_date_before_effective_returns_fallback(self):
        # claude-3-5-sonnet became effective 2024-10-22; date before → fallback
        rates = lookup_rates("claude-3-5-sonnet-20241022", "2024-01-01")
        # Should return fallback rates since no entry is effective yet
        from burnmap.pricing import _FALLBACK_RATES
        assert rates == _FALLBACK_RATES

    def test_date_on_effective_date_returns_rates(self):
        rates = lookup_rates("claude-3-5-sonnet-20241022", "2024-10-22")
        assert rates["input_per_1m"] == pytest.approx(3.0)

    def test_date_after_effective_date_returns_rates(self):
        rates = lookup_rates("claude-3-5-sonnet-20241022", "2025-06-15")
        assert rates["input_per_1m"] == pytest.approx(3.0)

    def test_accepts_date_object(self):
        rates = lookup_rates("claude-3-5-haiku-20241022", datetime.date(2025, 1, 1))
        assert rates["input_per_1m"] == pytest.approx(0.8)

    def test_accepts_none_date(self):
        # None → today, model should resolve without error
        rates = lookup_rates("claude-3-5-sonnet-20241022", None)
        assert rates["input_per_1m"] > 0

    def test_haiku_rates(self):
        rates = lookup_rates("claude-3-5-haiku-20241022", "2024-11-01")
        assert rates["input_per_1m"] == pytest.approx(0.8)
        assert rates["output_per_1m"] == pytest.approx(4.0)

    def test_returns_dict_copy(self):
        # Mutating result should not affect subsequent calls
        rates1 = lookup_rates("claude-3-5-sonnet-20241022", "2024-11-01")
        rates1["input_per_1m"] = 9999.0
        rates2 = lookup_rates("claude-3-5-sonnet-20241022", "2024-11-01")
        assert rates2["input_per_1m"] != 9999.0


class TestComputeCost:
    def test_basic_cost(self):
        # 1M input + 1M output at 3.0/15.0 = $18.00
        cost = compute_cost("claude-3-5-sonnet-20241022", 1_000_000, 1_000_000, date="2024-11-01")
        assert cost == pytest.approx(18.0, rel=1e-4)

    def test_zero_tokens_zero_cost(self):
        cost = compute_cost("claude-3-5-sonnet-20241022", 0, 0, date="2024-11-01")
        assert cost == 0.0

    def test_cached_tokens_cheaper(self):
        cost_no_cache = compute_cost("claude-3-5-sonnet-20241022", 1000, 0, date="2024-11-01")
        cost_cached = compute_cost("claude-3-5-sonnet-20241022", 0, 0, cached_tokens=1000, date="2024-11-01")
        assert cost_cached < cost_no_cache

    def test_unknown_model_uses_fallback(self):
        cost = compute_cost("unknown-model", 1_000_000, 0, date="2024-01-01")
        assert cost > 0  # fallback rates applied


class TestBillingLabel:
    def test_slash_is_synthetic(self):
        assert billing_label("slash") == LABEL_SYNTHETIC

    def test_skill_is_synthetic(self):
        assert billing_label("skill") == LABEL_SYNTHETIC

    def test_tool_is_synthetic(self):
        assert billing_label("tool") == LABEL_SYNTHETIC

    def test_subagent_is_real(self):
        assert billing_label("subagent") == LABEL_REAL

    def test_turn_is_real(self):
        assert billing_label("turn") == LABEL_REAL

    def test_unknown_kind_is_real(self):
        assert billing_label("api_call") == LABEL_REAL
