# Backend 模块重构：Canonical Import 残留导致应用与测试无法收集

## 1. 发生时间

2026-08-24

## 2. 问题范围

Workflow 领域完成旧入口物理删除后，仍有生产代码引用已删除的 `app.services.workflow_execution` 与 `app.services.workflow_governance`。其中 Webhook Trigger 服务仍依赖旧入口，Workflow Runtime 还保留旧 Execution 的延迟 import。

## 3. 实际表现

本地执行 `uv run python -c "from app.main import app; print('APP_IMPORT_OK')"` 时出现 `ModuleNotFoundError`；Workflow targeted tests、Webhook tests 以及 Backend Regression 在测试收集阶段因此失败。

同时，模块重构 Gate 的目标是旧模块路径必须为 0，因此不能通过重新创建兼容垫片解决。

## 4. 根因

本次 Workflow 完整迁移已经删除旧 Service 文件，但部分调用方没有在同一个迁移单元内完成 canonical import 切换：

- `app.services.webhook_trigger` 仍直接导入旧 Workflow Execution / Governance 路径；
- `app.runtime.workflow_runtime` 的执行方法仍使用旧 Execution 路径进行延迟 import。

这属于完整模块迁移中的 import residue，而不是新的业务实现缺失。

## 5. 修复原则

按照 `docs/01-governance/DEVELOPMENT.md` 与 Backend Module Architecture 的完全重构原则：

1. 生产代码直接使用 `app.services.workflow` 正式入口；
2. Runtime 直接依赖 Workflow 领域正式入口，不保留旧路径转发；
3. 不恢复旧文件，不创建兼容垫片，不复制第二套实现；
4. 保持 API Contract、数据库结构、Runtime 业务语义不变；
5. 相关模块继续补充中文职责、边界和关键依赖说明。

## 6. 验证要求

本地必须重新执行：

```powershell
cd backend
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"
uv run pytest -q tests/unit -k 'workflow or webhook'
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1
uv run pytest -q
```

记录以上命令的实际本地结果；未执行的结果不得标记为通过。
