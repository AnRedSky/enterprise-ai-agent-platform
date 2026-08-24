# API v1 重构后的旧 API import 残留

## 1. 发现时间

2026-08-24

## 2. 现象

API v1 物理迁移完成后，本地 API v1 Module Gate 与 Backend Regression 在测试收集阶段发现测试仍引用已删除的旧 API 模块路径：

- `app.api.tools`
- `app.api.runtime`
- `app.api.agents`
- `app.api.chat`

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

同时补充测试模块职责、边界与关键依赖的中文说明，避免通过旧入口恢复兼容层。

## 5. 验证状态

修复已直接提交 `main`。由于当前执行环境无法解析 GitHub 网络地址，无法在本环境重新拉取仓库并执行 pytest；因此本记录不预填测试通过结果。

开发者本地必须重新执行 API v1 Module Gate、Module Refactor Gate、Dependency Boundary Gate 与 `uv run pytest -q`，以实际结果作为验收依据。

## 6. 相关规则

- `docs/01-governance/DEVELOPMENT.md`
- `docs/00-architecture/BACKEND_MODULE_MIGRATION_MAP.md`
- `backend/scripts/test/module-refactor/03_backend_api_v1_module_gate.ps1`
