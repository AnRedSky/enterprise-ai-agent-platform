# Real API 注册 Membership 运行态漂移

## 1. 现象

Tenant-safe Real API bootstrap 在 `POST /auth/register` 成功后，调用 `GET /organizations/{organization_id}/members` 无法找到刚注册用户的 membership：

```text
RuntimeError: Registered fixture user is not present in the default Organization membership list
```

当前远端 `main` 基线为 `f17ac8d182e6d987f40a7f78927229ef85bffe2b`，该版本的正式 `/auth/register` 已在同一事务中创建 `User`、`UserRole` 与默认 Organization 的 active `OrganizationMembership`。

## 2. 根因判定策略

该错误不能直接归因于生产注册逻辑，也不能通过测试夹具再次 POST `/members` 掩盖问题，因为这会与正式注册语义重复并产生 409。

Tenant-safe bootstrap 现在在 HTTP 列表缺失时查询独立数据库连接：

- 数据库存在对应 membership：注册事务已经正确持久化，问题属于当前 API Service 运行实例、代码版本或 HTTP 读取路径漂移；
- 数据库不存在对应 membership：才判定为注册持久化缺陷，应继续定位生产 `/auth/register` 事务。

## 3. 本次代码修复

`backend/scripts/test/api-real/00_bootstrap_real_api_tenant_safe.py` 增加 `_registered_membership()` 数据库事实查询，并把原来的模糊错误拆分为两类确定性错误。

该诊断只读取测试事实，不修改生产数据，不创建或启动任何服务。

## 4. 服务启动边界

根据 `docs/01-governance/DEVELOPMENT.md`，Real API Gate 禁止自动创建、启动、重启或停止 API、Worker、Scheduler、PostgreSQL、Redis。

因此当数据库已经存在 membership、HTTP 读取却不可见时，Gate 必须停止并要求从最新 `main` 手动重启 API Service；不得在脚本中实现自动重启。

## 5. 验证流程

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend

git fetch origin
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
git rev-parse origin/main

# 手动从最新 main 重启现有 API Service；Gate 不执行服务生命周期管理。

uv run python .\scripts\test\api-real\00_bootstrap_real_api_tenant_safe.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

## 6. 验收要求

不得以“数据库中有 membership”替代 HTTP Real API 验收。最终必须由真实 HTTP `/auth/register` → `/organizations/{id}/members` → membership role update → 后续 Real API 测试完整通过。
