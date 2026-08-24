# API v1 重构后的旧 API import 残留

## 1. 发现时间

2026-08-24

## 2. 现象

API v1 物理迁移完成后，本地 API v1 Module Gate 与 Backend Regression 在测试收集阶段发现测试仍引用已删除的旧 API 模块路径：

- `app.api.tools`
- `app.api.runtime`
- `app.api.agents`
- `app.api.chat`
- `app.api.workflows`

其中生产代码已迁移到 `app.api.v1.<domain>`，旧路径不存在，因此 pytest 出现 `ModuleNotFoundError`。

## 3. 根因

本次 API 目录重构遵循“删除旧文件、禁止兼容垫片”的规则，但部分 API Contract / Integration 测试未同步完成 import 路径迁移，导致测试边界与生产代码的新正式入口不一致。

## 4. 修复

将受影响测试切换到 canonical API v1 入口：

- `app.api.v1.tools.router.list_tools`
- `app.api.v1.runtime.router._runtime_claims`
- `app.api.v1.runtime.router.RuntimeQueryService`
- `app.api.v1.agents.router.KnowledgeConfig`
- `app.api.v1.agents.router.VersionCreate`
- `app.api.v1.agents.chat.build_knowledge_context`
- `app.api.v1.workflows.router.WorkflowTriggerCreate`
- `app.api.v1.workflows.router.WorkflowTriggerUpdate`

同时为 `app.api.v1.workflows.router`、受影响 Contract 测试补充中文职责、边界与关键依赖说明，保持测试只引用正式 v1 入口，不恢复旧 API 兼容层。

## 5. 后续真实反馈

用户本地在完成前一轮 API v1 import 修复后重新执行 Gate，又发现 `tests/api_contract/test_api_scheduled_triggers.py` 与 `tests/api_contract/test_api_webhooks.py` 仍存在 `app.api.workflows` 动态 import。该问题已按同一根因继续修复。

当前代码修复已经直接提交 `main`，但本环境未执行用户本地 Windows `uv` / PowerShell Gate，因此不预填测试通过结果。

## 6. 验证要求

开发者本地必须重新执行：

1. API v1 Module Gate；
2. Backend Module Refactor Gate；
3. Dependency Boundary Gate；
4. `uv run pytest -q`。

只有旧 import 搜索为 0、API Contract 与 Backend Regression 全部实际通过后，API v1 才能进入最终重构 Gate。

## 7. 相关规则

- `docs/01-governance/DEVELOPMENT.md`
- `docs/00-architecture/BACKEND_MODULE_MIGRATION_MAP.md`
- `backend/scripts/test/module-refactor/03_backend_api_v1_module_gate.ps1`
