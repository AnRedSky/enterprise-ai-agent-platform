# 错误跟踪记录

本目录独立记录开发过程中已经发生并完成分析的错误，目标是形成可检索、可复用的工程经验，避免同类问题重复发生。

## 记录规则

1. 每个已确认的工程错误单独建立记录文件。
2. 文件名使用递增编号 + 简短问题名称，例如 `001-alembic-version-column-too-short.md`。
3. 必须记录：发生阶段、实际错误、根因、影响、修复方案、预防措施、验证命令、实际验证结果。
4. 不记录密码、Token、API Key、数据库密码等敏感信息。
5. 错误记录只描述已经发生或已经验证的问题，不得预填“已通过”。
6. 如果错误导致任务阻塞，必须同步更新 `docs/PROJECT_STATUS.md` 与对应 Phase 计划。
7. 修复代码后必须把错误记录纳入后续开发评审与测试检查项。

## 当前记录

- `001-alembic-version-column-too-short.md`：Phase 1.5-C migration revision id 超过历史 `alembic_version.version_num VARCHAR(32)` 长度导致 PostgreSQL migration 在更新 head 时失败。
- `002-backend-frontend-test-gate-coupling.md`：Phase 1.5 测试治理中 Backend / Frontend Gate 曾发生跨技术栈耦合，已拆分并固化独立 Gate 规则。
- `003-circuit-breaker-state-initialization.md`：Phase 1.5-G Circuit Breaker 新建状态在 flush 前计数值可能为 `None`，导致首次 failure 与 Real API bootstrap 异常，已完成状态初始化治理并纳入回归检查。
