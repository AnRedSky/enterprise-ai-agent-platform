# 2026-09-04 Phase 2.10-II Operator Audit Gate Coverage Gap

## 1. 问题

开发者在最新 `main` 本地执行 `26_operator_audit_query_performance_gate.ps1` 时，Gate 通过，但原 Gate 的 PostgreSQL Acceptance 实际只执行了三个 `tests/api_real` 文件，没有执行已经提交的 Retry / Resume 跨 Session 并发验收；同时脚本名称包含 `performance`，但原实现只验证索引存在，没有验证查询路径是否能够使用 Canonical 索引。

## 2. 根因

Gate 编排在并发验收测试提交后没有同步扩展，导致测试实现与 Gate 覆盖范围发生漂移。数据库索引 Acceptance 只验证 `pg_indexes` 元数据，无法发现查询语句未来绕过 tenant-first 索引的回归，因此“performance”名称与实际验收语义不一致。

## 3. 修复

1. 将 `tests/integration/test_operator_action_idempotency.py` 纳入 Operator Governance PostgreSQL Acceptance。
2. 将 `tests/integration/test_operator_execution_retry_resume_concurrency.py` 纳入同一 Gate，并由 Gate 自动设置 `RUN_DATABASE_INTEGRATION=1`，不要求人工修改测试环境或测试代码。
3. 新增 `tests/api_real/test_operator_audit_query_performance_acceptance.py`，针对 action、actor、resource、execution、trace、operator_action 六条正式查询路径执行 PostgreSQL `EXPLAIN`，关闭单次事务内的 sequential scan 作为稳定 Gate 条件，验证对应 Canonical tenant-first 索引可被查询计划使用。
4. 保持服务边界：Gate 仍只探测 PostgreSQL，不自动启动、停止或重启 API、Worker、Scheduler、PostgreSQL、Redis。
5. 保持警告策略：所有新增测试继续使用 `-W error`。

## 4. 验证要求

代码提交后必须由开发者在本地 Windows 环境执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\26_operator_audit_query_performance_gate.ps1
```

此外按 Backend 固定顺序执行：

```powershell
cd backend
uv run pytest -q -W error -s
uv run alembic upgrade head
```

本次代码修改未把尚未实际执行的本地结果标记为通过；真实 PostgreSQL 并发与查询计划结果必须以开发者本地输出为最终证据。
