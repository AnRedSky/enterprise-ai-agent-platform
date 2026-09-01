# 2026-09-01 Operator Audit 查询路由未注册

## 1. 问题现象

Phase 2.10-II Operator Audit Governance Backend Gate 的 API Contract 阶段全部失败：

- `GET /api/v1/runtime/operations/operator-audits` 路由未出现在 `app.routes`；
- 未认证请求返回 `404` 而不是 `401`；
- OpenAPI 中不存在对应 path，导致响应模型与参数边界断言失败。

## 2. 根因

`backend/app/api/v1/runtime/operator_audit.py` 已经实现完整的 Operator Audit 查询 Router，`backend/app/services/runtime_operations/operator_audit.py` 也已经提供查询服务，并通过 `runtime_operations.__init__` 正式暴露。

但是 `backend/app/main.py` 只注册了 Runtime Operator Action 与 Batch Operator Action Router，没有 import 或 `include_router` Operator Audit Router。因此实现存在于代码库中，却没有进入 FastAPI 应用路由表。

这属于应用装配层遗漏，而不是查询 Service、数据库模型或认证 Contract 的实现缺陷。

## 3. 修复

在 `backend/app/main.py`：

1. 增加 `runtime_operator_audit_router` import；
2. 调用 `app.include_router(runtime_operator_audit_router)` 注册 `/api/v1/runtime/operations/operator-audits`；
3. 保持 Operator Audit Router 自身的 Bearer authentication、tenant scope、查询参数约束及响应模型不变，避免重复实现业务逻辑。

## 4. 验证要求

开发者本地必须执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\24_operator_audit_governance_gate.ps1
```

Gate 不自动启动 API、Scheduler、Worker、PostgreSQL 或 Redis；PostgreSQL 缺失时只报告标准人工启动命令，不自动执行。

## 5. 预防

新增 API Router 后，必须在同一交付单元检查：

- `app.main` 路由注册；
- API Contract 路由发现；
- OpenAPI path / schema；
- 未认证边界；
- 必要时 Real PostgreSQL Acceptance；
- Backend Regression 与 warning-free 结果。
