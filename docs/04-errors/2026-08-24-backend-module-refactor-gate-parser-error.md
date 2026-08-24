# Backend 模块重构 Gate：PowerShell 脚本解析错误

## 1. 发生时间

2026-08-24

## 2. 问题范围

Workflow Canonical Import 循环依赖已经修复，应用导入与 Workflow targeted tests 已恢复；但模块化整改 Gate 脚本 `backend/scripts/test/module-refactor/01_backend_module_refactor_gate.ps1` 在本地执行阶段发生 PowerShell ParserError，导致 Gate 尚未真正开始执行。

## 3. 实际表现

本地执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1
```

在 wildcard filter 数组附近报告：

```text
You must provide a value expression following the '*' operator.
Unexpected token 'agent*' ...
Missing closing ')' after expression in 'if' statement.
The string is missing the terminator: '.
```

因此当前 `40 passed` 的 Workflow targeted tests 只能证明受影响 Workflow 测试已恢复，不能替代 Module Refactor Gate 的完整验收。

## 4. 根因

Gate 脚本中存在 PowerShell 字符串解析边界问题。错误首先定位到 `$filter` wildcard 数组，但后续解析错误向后级联，造成字符串、括号和代码块均被误报。

原脚本同时使用大量单引号字符串；为降低 PowerShell Parser 对 wildcard、正则表达式和中文字符串的歧义风险，本次修复统一改用双引号字符串，并对数组、函数参数与 Gate 调用结构进行明确换行。

## 5. 修复原则

1. 不改变模块重构 Gate 的业务验收规则；
2. 不通过跳过 Gate、关闭错误处理或兼容垫片绕过重构验收；
3. 保留旧文件删除、旧 import 为 0、重复实现检查、模块职责说明、targeted tests 与 Backend Regression；
4. 测试实现继续留在 `tests/`，脚本仅负责 Gate 与顺序编排；
5. 只有本地真实执行成功后，才更新 Workflow 等领域的迁移完成状态。

## 6. 本次修复

已修正：

- wildcard filter 数组的 PowerShell 字符串写法；
- Gate 脚本中的字符串、数组和代码块结构；
- Gate 调用的参数与脚本块格式；
- 保留 `$LASTEXITCODE` 失败传播逻辑，并在每个 Gate 步骤开始前显式初始化退出码。

## 7. 后续本地验证

```powershell
cd backend

git fetch origin
git reset --hard origin/main
git log -3 --oneline

uv run python -c "from app.main import app; print('APP_IMPORT_OK')"

git grep -n -E "app\.services\.workflow_execution|app\.services\.workflow_governance|app\.services\.workflow_registry" -- "*.py"

uv run pytest -q `
  tests/unit/test_workflow_execution_state_machine.py `
  tests/unit/test_workflow_execution_concurrency.py `
  tests/unit/test_workflow_execution_idempotency.py `
  tests/unit/test_workflow_execution_governance.py `
  tests/unit/test_workflow_execution_retry_transition.py `
  tests/unit/test_workflow_governance.py `
  tests/unit/test_workflow_publish_governance.py `
  tests/unit/test_workflow_retry_budget.py `
  tests/unit/test_workflow_retry_policy.py `
  tests/unit/test_workflow_runtime.py `
  tests/unit/test_workflow_runtime_timeout.py `
  tests/unit/test_webhook_trigger.py

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1

uv run pytest -q
```

未执行的结果不得记录为通过。