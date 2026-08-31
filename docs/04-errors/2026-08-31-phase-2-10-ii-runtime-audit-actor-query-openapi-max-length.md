# Phase 2.10-II Runtime Audit Actor 查询参数 OpenAPI 长度约束错误

## 1. 问题

`21_runtime_audit_action_outcome_hardening_gate.ps1` 的 API Contract 阶段在导入应用后可以正常启动，但 `test_runtime_audit_query_exposes_optional_actor_filter` 失败：

```text
KeyError: 'maxLength'
```

此前还出现过 FastAPI 路由注册阶段的错误：

```text
AssertionError: `Query` default value cannot be set in `Annotated` for 'actor'. Set the default value with `=` instead.
```

## 2. 根因

`actor` 参数同时使用了 `Annotated`、Pydantic `StringConstraints` 与 FastAPI `Query()`。当前 FastAPI/Pydantic 组合下，这种声明方式既容易触发 `Annotated` 默认值冲突，也不能稳定把 `max_length=128` 暴露为该 Query 参数的 OpenAPI `maxLength`。

本字段本身只是 HTTP Query 字符串过滤条件，不需要额外的 `StringConstraints` 层；直接使用 FastAPI `Query` 参数约束即可保持运行时校验和 OpenAPI 契约一致。

## 3. 修复

将 `actor` 从：

```python
actor: Annotated[str | None, StringConstraints(min_length=1, max_length=128), Query()] = None
```

调整为：

```python
actor: str | None = Query(None, min_length=1, max_length=128)
```

同时删除该路由文件中不再需要的 `Annotated` 与 `StringConstraints` 导入。

## 4. 验证要求

必须由本地开发环境实际执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\21_runtime_audit_action_outcome_hardening_gate.ps1
```

该 Gate 不创建、启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis；真实 PostgreSQL 验收继续使用自动生成的租户、审计事实和清理逻辑。

## 5. 预期结果

- Runtime Audit Query 路由保持 GET-only。
- `actor` 为可选 Query 参数。
- OpenAPI 中 `actor` schema 暴露 `maxLength: 128`。
- actor/action/outcome Contract 测试恢复通过。
- Real PostgreSQL acceptance 继续验证 tenant isolation 与 operational filtering。
