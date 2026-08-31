# ERR-0034：Runtime Audit Query actor 参数的 Annotated 默认值冲突

## 1. 问题现象

Phase 2.10-II Runtime Audit action + outcome hardening Gate 在收集 API Contract 测试时直接失败，FastAPI 在导入 `backend/app/api/v1/runtime/operations.py` 时抛出：

`AssertionError: Query default value cannot be set in Annotated for 'actor'. Set the default value with '=' instead.`

该错误发生在测试收集阶段，因此 Runtime Audit Query 的 Contract、targeted regression 与 Real PostgreSQL acceptance 均无法继续执行。

## 2. 根因

`actor` 查询参数同时使用了：

- `Annotated[..., Query(None)]`；
- 函数参数层面的 `= None`。

当前 FastAPI 版本禁止在 `Annotated` 内部的 `Query` 设置默认值，同时外部参数又重复提供默认值，导致依赖分析阶段直接拒绝注册路由。

此前为满足 actor 最大长度 Contract 引入的 `StringConstraints` 也是不必要的复杂化；项目中其他字符串查询参数已经直接通过 `Query(..., min_length=..., max_length=...)` 暴露 OpenAPI 约束。

## 3. 修复

将 `actor` 统一改为：

```python
actor: str | None = Query(None, min_length=1, max_length=128)
```

同时删除不再使用的 `typing.Annotated` 与 `pydantic.StringConstraints` 导入。

这样由 FastAPI 的 `Query` 直接承担：

- 可选参数语义；
- 最小长度 1；
- 最大长度 128；
- OpenAPI `maxLength: 128` 契约。

## 4. 预防

新增或修改 FastAPI 查询参数时，不在 `Annotated` 中重复设置 `Query` 默认值；同一参数的默认值只保留一个正式入口。参数约束优先采用项目既有的 `Query` 声明模式，避免为简单字符串约束引入重复的 Pydantic 元数据层。

## 5. 验证边界

代码修复已直接提交 `main`。开发者本地必须重新执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\21_runtime_audit_action_outcome_hardening_gate.ps1
```

在开发者本地结果返回前，不预填 Unit/API Contract、Real PostgreSQL 或 Backend Regression 的通过状态。
