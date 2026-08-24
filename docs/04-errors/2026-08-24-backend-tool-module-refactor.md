# Backend Tool 模块重构错误记录

## 1. 现象

本地 Module Refactor Gate 在前一基线已暴露两类问题：

- `app/services/observability_service` 等旧根 Service import 残留导致应用启动失败；
- Module Refactor Gate 使用 Windows PowerShell 5.1 默认代码页读取中文模块说明，导致脚本源码中的中文标记出现乱码并触发 ParserError。

同时，Tool 领域仍存在 `tool_audit`、`tool_observability`、`tool_rbac`、`tool_repository`、`tool_runtime_service` 五套并列服务包，与 Migration Map 要求的 `app.services.tool` 单一领域入口不一致。

## 2. 根因

Tool 的领域治理职责在前期迁移中被拆成多个根目录 Service 包，形成了多个正式 import 入口；API 与测试仍可能引用旧包名。

Gate 的模块说明检查直接依赖 PowerShell 源码中的中文字符串。Windows PowerShell 5.1 在未明确 UTF-8 编码时可能按系统代码页解析脚本，导致中文标记损坏并进一步产生 ParserError。

## 3. 影响

- 应用无法保证从 `app.main` 正常导入；
- Tool 领域存在重复入口风险；
- Gate 无法稳定执行模块说明检查；
- 在 Gate 未通过前不能宣称 Backend 模块重构完成，也不能恢复主线业务开发。

## 4. 修复

1. 将 Tool Runtime、RBAC、Audit、Observability、Repository 统一迁入 `app/services/tool/`。
2. 保留 `app/tools/` 作为 HTTP/Schema 等技术执行边界，不复制 Tool 领域治理逻辑。
3. 删除五个旧 Tool Service 包，不增加兼容转发层。
4. 更新 Tool API、单元测试和集成测试到 `app.services.tool` 正式入口。
5. Module Refactor Gate 改为使用 Python 按 UTF-8 读取源码检查 `职责：` 与 `边界：`，避免依赖 PowerShell 默认代码页。
6. 将 Tool 旧目录、旧 import、required files、targeted tests 纳入统一 Gate。

## 5. 验证要求

仓库端没有替代本地执行测试。本记录不宣称 Gate 或 Backend Regression 已通过。

开发者必须在最新 `main` 上依次执行：

```powershell
cd backend

git fetch origin
git reset --hard origin/main

uv run python -c "from app.main import app; print('APP_IMPORT_OK')"

git grep -n -E "app\.services\.tool_audit|app\.services\.tool_observability|app\.services\.tool_rbac|app\.services\.tool_repository|app\.services\.tool_runtime_service" -- "*.py"

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1

uv run pytest -q
```

任何旧 import、模块说明缺失、重复实现或测试失败都必须继续修复，禁止通过兼容垫片绕过 Gate。

## 6. 防重复措施

后续任何领域迁移必须先确定唯一 canonical package，再同步迁移生产 import、测试 import、文档与 Gate；禁止先保留旧目录再逐步增加第二套实现。