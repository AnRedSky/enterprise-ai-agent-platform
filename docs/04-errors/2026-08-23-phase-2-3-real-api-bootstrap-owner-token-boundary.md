# Phase 2.3 Real API Bootstrap Owner Token Boundary

## 发生时间

2026-08-23

## 问题

`backend/scripts/test/api-real/01_run_real_api_tests.ps1` 在 bootstrap 阶段仍可能出现：

```text
POST /workflows/executions/{id}/run -> expected HTTP 404, got 403
{"detail":"当前用户没有有效的 Organization membership"}
```

此前的修复已经把 Organization 创建提前到 Workflow fixtures 之前，但 bootstrap 在创建第二个 admin member 后，通过同一个 `httpx.Client` 登录 member，替换了当前 `Authorization` header。后续 Runtime fixture 因此不再显式使用本次创建 Organization 时的 owner session。

## 根因

Organization 创建服务会为创建者建立 active `owner` membership；因此 bootstrap owner token 本身满足 Runtime execution 的 Organization governance boundary。

原 helper 在创建 admin member 后执行 member login，并复用同一个 client：

1. owner 登录；
2. 创建 Organization，owner membership 已建立；
3. 创建 admin member；
4. member login 覆盖 `client.headers["Authorization"]`；
5. 后续 Workflow/Execution fixture 依赖被覆盖后的 session。

这违反了 bootstrap fixture 的 session ownership：tenant fixture 应由创建该 tenant 的 owner session 建立和运行，member token 只应保存给后续明确的 member-boundary 测试。

## 修复

新增 tenant-safe bootstrap entrypoint：

- `backend/scripts/test/api-real/00_bootstrap_real_api_tenant_safe.py`
- `backend/scripts/test/api-real/01_run_real_api_tests_tenant_safe.ps1`

修复实现通过独立 `httpx.Client` 完成 admin member login，避免修改 owner fixture client 的 Authorization header；owner token 继续用于创建和运行所有 Runtime fixtures，同时将 member token 写入测试 context，供后续组织成员权限场景使用。

该修复没有绕过任何 Organization membership / authorization 校验，也没有新增数据库结构，因此不需要 Alembic migration。

## 验证要求

开发者本地执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

然后执行：

```powershell
uv run pytest -q
uv run alembic upgrade head
```

Real API Gate 必须实际完成全部 `tests/api_real -m real_api` 后，才能标记为 Passed。

## 设计纪律

Real API bootstrap 不得通过降低鉴权、绕过 tenant boundary 或修改 Runtime 预期状态来修复测试；fixture session 必须与真实 Organization governance 规则一致。
