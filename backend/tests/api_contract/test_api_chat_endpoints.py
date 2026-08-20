from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_chat_routes_are_registered():
    paths={(route.path,tuple(sorted(route.methods or []))) for route in app.routes if route.path.startswith("/api/v1/agents/stream") or route.path.startswith("/api/v1/agents/sessions")}
    assert ("/api/v1/agents/stream",("POST",)) in paths
    assert ("/api/v1/agents/sessions/{session_id}/messages",("GET",)) in paths

def test_chat_stream_requires_bearer_authentication():
    assert client.post("/api/v1/agents/stream",json={"agent_id":"00000000-0000-0000-0000-000000000001","input":"hello"}).status_code==401

def test_chat_messages_requires_bearer_authentication():
    assert client.get("/api/v1/agents/sessions/00000000-0000-0000-0000-000000000001/messages").status_code==401
