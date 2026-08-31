# Phase 2.10-II Runtime Audit Query 路由前缀错误

## 1. 现象

开发者本地执行 Runtime Audit Query Unit / API Contract Gate 时，3 个 Contract 测试失败：

- 目标 GET 路由未注册；
- 未携带 Bearer Token 的请求返回 404，而 Contract 预期 401；
- `page_size=101` 的边界请求同样返回 404。

同时，Runtime Audit Query 的 Service 单元逻辑与真实 PostgreSQL tenant-isolation / operational filtering 验收已经具备，因此失败点位于 API 路由装配，而不是查询规则本身。

## 2. 根因

`backend/app/api/v1/runtime/router.py` 已经将 `operations_router` 作为子路由挂载在 `prefix="/api/v1/runtime"` 的 Runtime 聚合路由下。

原 `backend/app/api/v1/runtime/operations.py` 又声明了完整绝对前缀 `prefix="/api/v1/runtime/operations"`。FastAPI 子路由挂载时会进行前缀拼接，导致实际路径变成：

`/api/v1/runtime/api/v1/runtime/operations/...`

因此 Contract 查询的 `/api/v1/runtime/operations/audit/query` 实际不存在，表现为 404；鉴权和参数校验自然也不会进入目标 Endpoint。

## 3. 修复

将 `operations.py` 的 Router 前缀改为领域相对路径 `/operations`，由 Runtime 聚合路由统一提供 `/api/v1/runtime` 前缀。

同时在 Router 声明附近补充中文设计说明，明确该模块作为子路由挂载时不得再次声明 Runtime 根前缀。

## 4. 防回归

现有 Contract 测试继续强制验证：

1. `/api/v1/runtime/operations/audit/query` 仅注册 GET；
2. 未认证请求必须先经过 Bearer 鉴权并返回 401；
3. 非法 `page_size` 不得因为路由缺失而返回 404。

真实 PostgreSQL 验收继续覆盖 tenant isolation、action / resource / outcome / time-window operational filtering。

## 5. 结论

这是典型的聚合 Router 前缀重复拼接错误。修复不改变 Runtime Audit Query Service 的查询算法和 tenant boundary，只恢复既定 API Contract 的正确路由装配。
