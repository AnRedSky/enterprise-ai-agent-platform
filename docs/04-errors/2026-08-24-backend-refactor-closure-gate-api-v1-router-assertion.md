# 工程错误记录：Refactor Closure Gate 错误假设 `app.api.v1.router` 聚合入口

## 发生时间

2026-08-24

## 现象

用户在 Windows 本地执行 `05_backend_refactor_closure_gate.ps1` 时，Closure Gate 在“Canonical application import”阶段失败：

```text
ImportError: cannot import name 'router' from 'app.api.v1'
```

但同一基线下 API v1 Module Gate、Runtime Boundary Gate、Module Refactor Gate、Dependency Boundary Gate 以及 Backend default regression 均已由用户本地反馈通过。

## 根因

Closure Gate 将 `app.api.v1` 当作应暴露聚合 `router` 的模块，并执行：

```python
from app.api.v1 import router as api_router
```

实际架构中，`app.api.v1` 是 API 版本命名空间；各领域 Router 位于 `app/api/v1/<domain>/`，HTTP 路由由 `app.main` 显式注册。`app/api/v1/__init__.py` 只承担版本包职责说明，并没有也不应重复实现一个聚合 Router。

因此该失败属于 Gate 自身的错误断言，不是业务代码重构回归。

## 修复

将 Closure Gate 的 canonical import 校验改为真实架构入口：

- `from app.main import app`：验证实际 FastAPI 应用及 API v1 路由注册入口；
- `from app.runtime.model import ModelGateway`：验证 Model Runtime canonical 导出；
- `from app.runtime.workflow import WorkflowRuntime`：验证 Workflow Runtime canonical 导出。

不新增 `app.api.v1.router`，不创建兼容垫片，不复制 HTTP Router。

## 验证要求

本修复直接提交 `main` 后，必须由用户本地重新执行 Closure Gate。Closure Gate 通过后，再按开发准则重新执行 API v1、Runtime Boundary、Module Refactor、Dependency Boundary 与 Backend Regression。未实际执行前不得记录为通过。
