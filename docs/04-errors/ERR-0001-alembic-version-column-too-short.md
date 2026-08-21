# ERR-0001 — Alembic revision id 超过 version_num 长度

- Legacy ID: `001-alembic-version-column-too-short`
- Phase: 1.5-C
- 类型: Database Migration / Alembic
- 严重级别: 阻塞

## 现象
`0016_workflow_execution_state_machine` 写入 `alembic_version.version_num` 时触发 `VARCHAR(32)` 截断。

## 根因
历史 `alembic_version.version_num` 容量与新 revision naming convention 不兼容。

## 修复
在 `backend/alembic/env.py` migration preflight 中将既有 `version_num` 小于 64 的列扩展为 `VARCHAR(64)`；新库不做额外操作。

## 预防 / 验证
Migration 必须实际执行 `uv run alembic upgrade head`、`alembic current` 与回归测试。原记录明确未重新执行前不得标记通过。
