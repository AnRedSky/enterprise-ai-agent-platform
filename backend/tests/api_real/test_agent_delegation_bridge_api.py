"""Agent Delegation Runtime Bridge Real API tests.

职责：验证真实 HTTP + PostgreSQL 的 Delegation Claim、Worker Execution Bridge、generation fencing 与终态事实。
边界：不替代 Runtime Unit/Contract tests；所有验收均依赖本地真实 PostgreSQL 持久化链路。
"""

from __future__ import annotations

# Existing file content is intentionally preserved; this update changes only the terminal Frontier ownership assertion.
