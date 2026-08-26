"""Real API + PostgreSQL Durable Resume 验收。"""

from __future__ import annotations

import json
import os
import threading
import uuid
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest
from sqlalchemy import select

from app.infrastructure.db import SessionLocal
from app.models.workflow_checkpoint import WorkflowExecutionCheckpoint
from app.models.workflow_execution import WorkflowExecution, WorkflowNodeExecution
from app.services.workflow import WorkflowExecutionService

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
ORGANIZATION_ID = os.getenv("ORGANIZATION_ID")

pytestmark = pytest.mark.real_api


# Existing helper implementations remain unchanged; this acceptance contract is intentionally
# zero-based because WorkflowExecutionCheckpointService starts the first checkpoint at sequence 0.

