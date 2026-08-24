# 2026-08-24 Backend Module Refactor：Runtime Query Gate 误报 canonical package

## 1. 问题

本地执行 Backend Module Refactor Gate 时，`git grep` 将 `app.services.runtime_query` 判定为 legacy import。该路径同时又是当前 Migration Map 定义的 Runtime Query canonical package 入口，因此 Gate 与模块迁移规则发生冲突。

## 2. 根因

Runtime Query 已物理迁移到：

```text
app/services/runtime_query/
├── __init__.py
└── service.py
```

正式导入入口就是 `app.services.runtime_query`。原 Gate 的 legacy pattern 使用完整前缀 `app\.services\.runtime_query`，无法区分“已迁移的 package import”和“已删除的旧根文件 `app/services/runtime_query.py`”。

旧根文件是否存在已经由 `forbiddenPaths` 单独检查，因此该 grep 规则属于重复且错误的约束，会把所有合法 canonical import 一并拦截。

## 3. 修复

- 从 `legacyImportPatterns` 删除 `app\.services\.runtime_query`。
- 保留 `app/services/runtime_query.py` 的 `forbiddenPaths` 检查，继续禁止旧物理文件。
- 保留 `app/services/runtime_query/__init__.py` 作为唯一正式入口。
- 不增加兼容垫片，不增加第二套 Runtime Query 实现。
- 为 `app/services/runtime_query/service.py` 补充中文职责、边界与关键依赖说明。

## 4. 验证要求

开发者本地同步最新 `main` 后执行：

```powershell
cd backend
git fetch origin
git reset --hard origin/main

uv run python -c "from app.main import app; print('APP_IMPORT_OK')"

git grep -n -E "app\.services\.circuit_breaker|app\.services\.workflow_trigger|app\.services\.workflow_trigger_schedule|app\.services\.webhook_trigger|app\.services\.tool_audit|app\.services\.tool_observability|app\.services\.tool_rbac|app\.services\.tool_repository|app\.services\.tool_runtime_service|app\.services\.observability_service|app\.services\.retrieval_evaluation_" -- "*.py"

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1
```

Gate 通过后继续：

```powershell
uv run pytest -q
```

## 5. 完成标准

- Runtime Query canonical import 不再被 Gate 误报；
- `app/services/runtime_query.py` 旧根文件仍不存在；
- Runtime Query targeted tests 与 Workflow/Trigger tests 通过；
- Module Refactor Gate 继续执行后续真实 blocker 检查；
- 不使用兼容垫片或重复实现。

## 6. 状态

**Gate 规则已修复，待开发者本地重新执行验证。**

本记录不代表本地 Gate 或 Backend Regression 已通过。