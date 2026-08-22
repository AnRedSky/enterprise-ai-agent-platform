from app.main import app


def test_agent_contract_exposes_governed_model_profile_selection():
    schema = app.openapi()
    agent_create = schema["components"]["schemas"]["AgentCreate"]
    version_create = schema["components"]["schemas"]["VersionCreate"]
    assert agent_create["properties"]["model_profile_id"]["anyOf"] == [{"type": "string", "format": "uuid"}, {"type": "null"}]
    assert version_create["properties"]["model_profile_id"]["anyOf"] == [{"type": "string", "format": "uuid"}, {"type": "null"}]


def test_runtime_trace_contract_exposes_model_profile_and_provider_identity():
    schema = app.openapi()
    execution = schema["components"]["schemas"]["ExecutionItem"]["properties"]
    event = schema["components"]["schemas"]["ExecutionEventItem"]["properties"]
    assert execution["model_profile_id"]["anyOf"] == [{"type": "string", "format": "uuid"}, {"type": "null"}]
    assert event["model_profile_id"]["anyOf"] == [{"type": "string", "format": "uuid"}, {"type": "null"}]
    assert event["provider_id"]["anyOf"] == [{"type": "string", "format": "uuid"}, {"type": "null"}]
