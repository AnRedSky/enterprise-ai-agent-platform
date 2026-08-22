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

    # Pydantic v2 represents an optional integer as a nullable union in OpenAPI.
    # Keep the contract focused on the semantic constraints rather than the exact
    # ordering/shape of union branches emitted by a particular Pydantic version.
    dimension_schema = provider_schema["properties"]["dimension"]
    integer_schema = next(branch for branch in dimension_schema["anyOf"] if branch.get("type") == "integer")
    assert integer_schema["minimum"] == 1.0
    assert {branch.get("type") for branch in dimension_schema["anyOf"]} == {"integer", "null"}

    assert "credential_ref" in schema["components"]["schemas"]["ModelProviderCreate"]["properties"]
