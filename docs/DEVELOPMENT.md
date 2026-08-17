# 开发文档

## 1. 技术基线

- Backend：FastAPI + Python 3.12
- Frontend：Vue 3 + TypeScript + Vite
- Database：PostgreSQL
- Cache：Redis
- Migration：Alembic
- Test：pytest
- CI：GitHub Actions

## 2. 分层原则

```text
API → Service → Runtime → Gateway / Tool / Memory
                    ↓
                 Repository
                    ↓
               PostgreSQL / Redis
```

API 层只负责协议适配与鉴权；业务规则进入 Service；Agent 执行进入 Runtime；模型供应商差异必须封装在 Model Gateway；Tool 必须经过 Registry 和权限校验。

## 3. Agent 执行标识

每次执行至少保持以下关联：

`request_id`、`trace_id`、`session_id`、`agent_id`、`agent_version`、`model_id`、`execution_id`。

## 4. Phase 1.3 优先级

1. Model Gateway：OpenAI-compatible Provider、流式、Usage、超时与错误边界。
2. Tool Runtime：Schema、权限、超时、执行限制与审计。
3. Memory：Session 上下文与长期记忆基础能力。
4. Observability：执行链路、耗时、Token、错误与审计。
5. Vue 管理端：登录、Agent、Session、调试。

## 5. 开发约束

- 所有 API 使用 `/api/v1`。
- 数据库结构必须通过 Alembic 迁移变更。
- 不提交 `.env`、密钥、日志、构建产物、IDE 配置、临时压缩包或个人文件。
- 不允许任意 Python、Shell 或未经授权的 URL 执行作为 Tool。
- 新功能必须有对应测试；修复必须补回归测试。
- Commit 使用 Conventional Commits，例如 `feat:`, `fix:`, `docs:`, `test:`, `chore:`。
- 每个阶段完成后先验证 GitHub 分支完整性和 CI，再进入下一阶段。
