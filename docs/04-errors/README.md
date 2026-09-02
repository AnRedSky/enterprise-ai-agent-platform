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
| ERR-0021 | 2026-08-22 | Scheduled Trigger 与 Real Retrieval Gate 回归失败 |
| ERR-0022 | 2026-08-22 | Real Provider baseline 缺失导致 Real API trace gate 阻塞 |
| ERR-0023 | 2026-08-23 | Knowledge Retrieval Real Provider 评估脚本旧 Provider 导入路径 |
| ERR-0024 | 2026-08-23 | Backend 模块重构后的测试边界残留 |
| ERR-0025 | 2026-08-24 | Backend Refactor Closure Gate 将 canonical Service 包入口误判为旧 import |
| ERR-0026 | 2026-08-26 | Real API Trigger 测试专用事件循环被 pytest 生命周期提前关闭 |
| ERR-0027 | 2026-08-28 | Frontier completion 当前 lifecycle 与目标 lifecycle 混淆导致 stale Worker fencing 被遮蔽 |
| ERR-0028 | 2026-08-28 | Phase 2.7 本地回归中的测试 Contract / Double 漂移 |
| ERR-0029 | 2026-08-28 | B2 Synthetic Runtime 被 DAG Contract 错误拦截 |
| ERR-0030 | 2026-08-29 | Delegation Claim 创建 Execution 后未进入 Durable Frontier |
| ERR-0031 | 2026-08-29 | Frontend SSE Reader Double 与 Runtime Status Contract 漂移 |
| ERR-0032 | 2026-08-30 | Runtime Metric Contract 部分指标导出与 Real Acceptance fixture 唯一键冲突 |
| ERR-0033 | 2026-08-31 | Global Runtime Operations Agent Filter SQL Contract 漂移 |
| ERR-0034 | 2026-08-31 | Runtime Audit Query actor 参数 Annotated 默认值冲突 |
| ERR-0035 | 2026-09-01 | Operator Audit Real Acceptance actor 外键夹具未显式建立持久化依赖顺序 |
| ERR-0036 | 2026-09-02 | Real API Tenant 清理遗漏 Durable Integration Event 外键依赖 |

## 迁移规则

- 错误正文保留问题现象、根因、修复、预防和验证边界。
- 历史错误不得因为已修复而删除其事实记录。
- 测试结果必须区分“代码修复完成”和“开发者实际验证通过”。
- 新错误不得继续放入 `docs/error-tracking/`。
