from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
pytestmark = pytest.mark.real_api


def _load_real_api_context() -> None:
    global TOKEN
    context_file = Path(__file__).parents[2] / "scripts" / "test" / "api-real" / ".real_api_context.json"
    if context_file.exists():
        context = json.loads(context_file.read_text(encoding="utf-8"))
        # Retrieval evaluation trace is intentionally admin-only. The bootstrap
        # creates a dedicated organization-admin member token for privileged
        # real-API validation; prefer it over the default fixture owner's token.
        admin_token = context.get("ORGANIZATION_MEMBER_ACCESS_TOKEN")
        if admin_token:
            TOKEN = admin_token
    if not TOKEN:
        TOKEN = os.getenv("ADMIN_ACCESS_TOKEN")


_load_real_api_context()


def _client() -> httpx.Client:
    if not TOKEN:
        pytest.fail("ADMIN_ACCESS_TOKEN or ACCESS_TOKEN is required for real API validation; run 01_run_real_api_tests.ps1 first")
    return httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=30.0,
    )


def test_real_provider_evaluation_trace_is_persisted_and_queryable():
    runner = Path(__file__).parents[2] / "scripts" / "evaluation" / "knowledge" / "run_knowledge_retrieval_real_provider.py"
    result = subprocess.run(
        [sys.executable, str(runner), "--k", "3"],
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    report = json.loads(result.stdout)
    evaluation_run_id = report["evaluation_run_id"]

    with _client() as client:
        trace = client.get(f"/runtime/retrieval-evaluations/{evaluation_run_id}")
        assert trace.status_code == 200, trace.text
        payload = trace.json()
        assert payload["execution"]["trace_id"] == evaluation_run_id
        assert payload["execution"]["status"] == "completed"
        events = payload["items"]
        span_types = {item["span_type"] for item in events}
        assert "retrieval_evaluation_case" in span_types
        assert "retrieval_evaluation_summary" in span_types
        summary = next(item for item in events if item["span_type"] == "retrieval_evaluation_summary")
        assert summary["metadata"]["evaluation_run_id"] == evaluation_run_id
        assert summary["metadata"]["provider"] == report["provider"]
        assert summary["metadata"]["model"] == report["model"]
        assert summary["metadata"]["embedding_dimension"] == report["embedding_dimension"]
        assert summary["metadata"]["top_k"] == report["top_k"]

        audit = client.get("/runtime/audit-logs", params={"status": "success", "page": 1, "page_size": 100})
        assert audit.status_code == 200, audit.text
        matching = [
            item
            for item in audit.json()["items"]
            if item["action"] == "retrieval_evaluation.completed"
            and item.get("execution_id") == payload["execution"]["execution_id"]
        ]
        assert matching, audit.text
