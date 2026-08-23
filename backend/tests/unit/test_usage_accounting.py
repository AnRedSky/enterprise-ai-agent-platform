from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.usage_accounting import UsageAccountingService


def test_calculate_cost_uses_token_and_request_units():
    result = UsageAccountingService.calculate_cost(
        1500,
        500,
        1,
        Decimal("0.002"),
        Decimal("0.004"),
        Decimal("0.001"),
    )
    input_cost, output_cost, request_cost, total_cost, units = result
    assert input_cost == Decimal("0.003")
    assert output_cost == Decimal("0.002")
    assert request_cost == Decimal("0.001")
    assert total_cost == Decimal("0.006")
    assert units == ["request", "input_token", "output_token"]


def test_calculate_cost_keeps_failed_attempt_as_request_usage_only():
    result = UsageAccountingService.calculate_cost(
        None,
        None,
        1,
        Decimal("0.002"),
        Decimal("0.004"),
        Decimal("0.001"),
    )
    assert result[0:4] == (Decimal("0"), Decimal("0"), Decimal("0.001"), Decimal("0.001"))
    assert result[4] == ["request"]


def test_pricing_from_profile_defaults_to_unconfigured_without_secret_data():
    profile = SimpleNamespace(parameters={})
    assert UsageAccountingService.pricing_from_profile(profile) == (
        "provider_pricing", "unconfigured", Decimal("0"), Decimal("0"), Decimal("0")
    )


def test_pricing_from_profile_rejects_negative_rates():
    profile = SimpleNamespace(parameters={"pricing": {"input_token_per_1k": -1}})
    with pytest.raises(Exception, match="non-negative"):
        UsageAccountingService.pricing_from_profile(profile)
