import hashlib

import pytest

from app.services.workflow_trigger_schedule import validate_trigger_config, verify_webhook_secret


SECRET = "phase-1-8-webhook-secret"


def test_webhook_config_hashes_secret_and_preserves_public_contract():
    config = validate_trigger_config(
        "webhook",
        {"auth_mode": "secret", "secret": SECRET, "event_id_field": "event_id"},
    )

    assert config["auth_mode"] == "secret"
    assert config["event_id_field"] == "event_id"
    assert config["secret_hash"] == hashlib.sha256(SECRET.encode()).hexdigest()
    assert "secret" not in config


def test_webhook_secret_verification_does_not_accept_wrong_secret():
    config = validate_trigger_config("webhook", {"secret": SECRET})

    assert verify_webhook_secret(config, SECRET) is True
    assert verify_webhook_secret(config, "wrong-phase-1-8-secret") is False
    assert verify_webhook_secret(config, None) is False


def test_webhook_secret_requires_minimum_length():
    with pytest.raises(ValueError, match="16-256"):
        validate_trigger_config("webhook", {"secret": "too-short"})


def test_webhook_auth_mode_is_restricted_to_secret():
    with pytest.raises(ValueError, match="auth_mode"):
        validate_trigger_config(
            "webhook",
            {"auth_mode": "oauth", "secret": SECRET},
        )
