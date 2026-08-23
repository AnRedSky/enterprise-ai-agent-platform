from uuid import uuid4

import pytest

from app.services.model_provider_governance_contract import (
    CostPolicy,
    CostUnit,
    FallbackPolicy,
    FallbackReason,
    PricingSource,
    ProviderCandidate,
    RoutingRequest,
    RoutingStrategy,
    UsageIdentity,
    ProviderGovernanceContract,
    select_candidates,
    usage_dimensions,
)


ORG = uuid4()
PROVIDER_A = uuid4()
PROVIDER_B = uuid4()
PROFILE_A = uuid4()
PROFILE_B = uuid4()


def candidate(*, provider_id, profile_id, default=False, capabilities=frozenset({"streaming"})):
    return ProviderCandidate(
        provider_id=provider_id,
        profile_id=profile_id,
        model_type="chat",
        model_name="fixture-model",
        enabled=True,
        is_default=default,
        capabilities=capabilities,
        provider_name=str(provider_id),
    )


def test_explicit_profile_never_implicitly_selects_another_profile():
    request = RoutingRequest(organization_id=ORG, model_type="chat", profile_id=PROFILE_A)
    result = select_candidates(
        request,
        [candidate(provider_id=PROVIDER_A, profile_id=PROFILE_A), candidate(provider_id=PROVIDER_B, profile_id=PROFILE_B)],
        RoutingStrategy.EXPLICIT_PROFILE,
    )
    assert [item.profile_id for item in result] == [PROFILE_A]


def test_explicit_strategy_requires_profile_identity():
    request = RoutingRequest(organization_id=ORG, model_type="chat")
    assert select_candidates(request, [candidate(provider_id=PROVIDER_A, profile_id=PROFILE_A, default=True)], RoutingStrategy.EXPLICIT_PROFILE) == []


def test_default_strategy_is_capability_and_provider_allowlist_scoped():
    request = RoutingRequest(
        organization_id=ORG,
        model_type="chat",
        required_capabilities=frozenset({"streaming"}),
        allowed_provider_ids=frozenset({PROVIDER_B}),
    )
    result = select_candidates(
        request,
        [candidate(provider_id=PROVIDER_A, profile_id=PROFILE_A, default=True), candidate(provider_id=PROVIDER_B, profile_id=PROFILE_B, default=True)],
        RoutingStrategy.ORGANIZATION_DEFAULT,
    )
    assert [item.provider_id for item in result] == [PROVIDER_B]


def test_fallback_policy_rejects_unbounded_attempts():
    with pytest.raises(ValueError, match="max_attempts"):
        FallbackPolicy(max_attempts=0)


def test_fallback_reasons_are_explicitly_transport_failures():
    policy = FallbackPolicy()
    assert policy.eligible_reasons == frozenset(FallbackReason)
    assert FallbackReason.PROVIDER_5XX in policy.eligible_reasons
    assert FallbackReason.TIMEOUT in policy.eligible_reasons


def test_cost_policy_requires_versioned_pricing_source():
    policy = CostPolicy(
        units=(CostUnit.INPUT_TOKEN, CostUnit.OUTPUT_TOKEN),
        pricing_source=PricingSource.PROVIDER_PRICING,
        pricing_version="2026-08",
    )
    assert policy.pricing_source is PricingSource.PROVIDER_PRICING
    assert policy.pricing_version == "2026-08"
    with pytest.raises(ValueError, match="pricing_version"):
        CostPolicy(units=(CostUnit.REQUEST,), pricing_source=PricingSource.PLATFORM_PRICING, pricing_version=" ")


def test_usage_identity_is_traceable_without_secret_material():
    identity = UsageIdentity(
        organization_id=ORG,
        provider_id=PROVIDER_A,
        profile_id=PROFILE_A,
        model_type="chat",
        request_id="req-1",
        trace_id="trace-1",
        outcome="success",
    )
    dimensions = usage_dimensions(identity)
    assert dimensions == {
        "organization_id": str(ORG),
        "provider_id": str(PROVIDER_A),
        "profile_id": str(PROFILE_A),
        "model_type": "chat",
        "request_id": "req-1",
        "trace_id": "trace-1",
        "outcome": "success",
    }
    assert "credential" not in dimensions
    assert "api_key" not in dimensions


def test_phase_2_3_contract_has_explicit_defaults():
    contract = ProviderGovernanceContract()
    assert contract.routing_strategy is RoutingStrategy.EXPLICIT_PROFILE
    assert contract.fallback.max_attempts == 2
    assert contract.cost.pricing_source is PricingSource.PROVIDER_PRICING
