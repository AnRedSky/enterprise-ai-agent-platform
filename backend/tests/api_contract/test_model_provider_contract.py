from app.main import app


def test_model_provider_routes_are_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/model-providers" in paths
    assert "/api/v1/model-providers/{provider_id}" in paths
    assert "/api/v1/model-providers/{provider_id}/profiles" in paths
    assert "/api/v1/model-providers/model-profiles/{profile_id}" in paths


def test_model_provider_openapi_exposes_chat_and_embedding_profiles():
    schema = app.openapi()
    provider_schema = schema["components"]["schemas"]["ModelProfileCreate"]
    assert provider_schema["properties"]["model_type"]["pattern"] == "^(chat|embedding)$"
    assert provider_schema["properties"]["dimension"]["type"] == "integer"
    assert "credential_ref" in schema["components"]["schemas"]["ModelProviderCreate"]["properties"]
