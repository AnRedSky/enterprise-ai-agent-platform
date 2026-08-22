# 工程错误记录

本目录是唯一正式错误记录入口。新错误统一使用 `ERR-0001-description.md` 命名；Legacy ID 保留在正文用于历史追溯。

## 当前记录

| Canonical ID | Legacy 来源 | 主题 |
|---|---|---|
| ERR-0001 | 001 | Alembic version_num 容量 |
| ERR-0002 | 002 | Alembic env 测试导入 |
| ERR-0003 | 002 | Backend/Frontend Gate 耦合 |
| ERR-0004 | 002 | Real API 注册 500 |
| ERR-0005 | 003 | Circuit State 初始化 |
| ERR-0006 | 003 | Governance created_by fixture |
| ERR-0007 | 004 | Playwright project |
| ERR-0008 | 004 | Governance tenant/workflow fixture |
| ERR-0009 | 005 | AsyncMock / AsyncSession.add |
| ERR-0010 | 006 | Vite/Rollup warning |
| ERR-0011 | 007 | Real API 空 Workflow bootstrap |
| ERR-0012 | 008 | Retry/Circuit boundary |
| ERR-0013 | 009 | Test Gate 隔离 |
| ERR-0014 | 010 | Node/Workflow timeout classification |
| ERR-0015 | 011 | Circuit policy / HALF_OPEN probe |
| ERR-0016 | 012 | Retry node state / deadline |
| ERR-0017 | 2026-08-21 | Scheduled multi-worker / MissingGreenlet |
| ERR-0018 | 2026-08-21 | Real API Idempotency race / AsyncSession rollback |
| ERR-0019 | 2026-08-21 | WorkflowRuntime 缺失 execute / Real API bootstrap 500 |
| ERR-0020 | 2026-08-22 | Organization Membership table row type / vue-tsc |

## 迁移规则

- 错误正文保留问题现象、根因、修复、预防和验证边界。
- 历史错误不得因为已修复而删除其事实记录。
- 测试结果必须区分“代码修复完成”和“开发者实际验证通过”。
- 新错误不得继续放入 `docs/error-tracking/`。
