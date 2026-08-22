from __future__ import annotations

import subprocess
import sys


def test_trace_service_registers_audit_foreign_key_models_in_clean_process():
    code = """
from app.models.core import Base
from app.services.retrieval_evaluation_trace import RetrievalEvaluationTraceService

required = {
    "workflows",
    "workflow_versions",
    "workflow_executions",
    "executions",
    "execution_events",
    "audit_logs",
}
missing = sorted(required - set(Base.metadata.tables))
if missing:
    raise SystemExit(f"missing trace model tables: {missing}")
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
