# Real API 注册 Membership 运行态漂移

## 1. 现象

Tenant-safe Real API bootstrap 在 `POST /auth/register` 成功后，调用 `GET /organizations/{organization_id}/members` 无法在第一页找到刚注册用户的 membership，并据此误报运行态漂移。

本地反馈中的 Organization 使用了长期复用的默认 Tenant。该 Organization 已累积超过单页默认容量的历史成员，因此新注册用户位于后续分页，而旧 bootstrap 只检查第一批 `items`。

## 2. 根因判定

生产 `/auth/register` 当前正式语义是在同一事务中创建 `User`、`UserRole` 与默认 Organization 的 active `OrganizationMembership`。因此当数据库已经存在 membership 时，不应再次 POST `/members`，也不应修改生产注册逻辑。

实际根因是 Tenant-safe bootstrap 的成员查询没有遵循 Organization membership API 的分页 Contract：

- `GET /organizations/{organization_id}/members` 默认只返回有限数量的成员；
- 成员按 `created_at`、`id` 升序返回；
- 长期复用 Organization 时，新注册成员可能位于第一页之后；
- bootstrap 只搜索 `items` 第一页，会把“未在第一页发现”错误解释为“HTTP 读路径漂移”。

项目此前的 Real API Organization Governance 测试已经通过 `_list_all_members()` 分页读取完整成员集合来避免同类误判。本次修复将同一规则补齐到 Tenant-safe bootstrap。

## 3. 修复

`backend/scripts/test/api-real/00_bootstrap_real_api_tenant_safe.py` 新增 `_find_membership()`：

1. 以 `offset=0, limit=50` 请求成员列表；
2. 在当前页搜索注册用户；
3. 未找到且尚有后续成员时继续下一页；
4. 找到后返回真实 membership ID；
5. 遍历完全部分页仍未找到时，才执行数据库持久事实诊断。

这样既保持真实 HTTP 验收，又不会通过直接写数据库或重复 POST `/members` 掩盖 Contract 问题。

## 4. 服务生命周期边界

根据 `docs/01-governance/DEVELOPMENT.md`，Real API Gate 不负责自动创建、启动、重启或停止 API、Worker、Scheduler、PostgreSQL、Redis。服务由开发者按标准命令手动运行，Gate 只负责探测与测试。

因此本次不修改服务启动逻辑，也不在测试脚本中加入进程管理。

## 5. 本地验证流程

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend

git fetch origin
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
git rev-parse origin/main

# 保持现有 API / Worker / Scheduler / PostgreSQL / Redis 运行实例；不要由 Gate 自动重启服务。

uv run python .\scripts\test\api-real\00_bootstrap_real_api_tenant_safe.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

## 6. 验收要求

最终验收必须继续走真实 HTTP：

`/auth/register` → `/organizations/{id}/members` 分页查询 → membership role update → 后续 Real API 测试。

数据库读取只能用于失败时区分“生产注册未持久化”与“HTTP Contract/运行态问题”，不能替代 Real API 验收。
