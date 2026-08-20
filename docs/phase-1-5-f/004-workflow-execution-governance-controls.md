# Phase 1.5-F / 004 Workflow Execution 执行治理增强

## 状态

已实现并提交到 `main`。

## 本次整改

在已有 Execution Timeline、Workflow Trace、Audit 与 Trace 持久化闭环基础上，补齐 Execution 级治理控制：

- `pending` / `running` Execution 支持 Cancel；
- `failed` Execution 支持 Retry；
- Retry 创建新的 Execution，并通过 `retry_of_execution_id` 保留原 Execution 血缘；
- Retry 复用原 Workflow Version 的已验证 definition，避免绕过 Runtime definition validation；
- Cancel / Retry 请求及新 Execution 创建均写入既有 Audit / Trace，不新增第二套治理模型；
- 保持 tenant 与 Execution RBAC 边界不变。

## 测试整改

本次回归发现 `test_retry_creates_new_execution_with_lineage` 的 AsyncMock 配置与真实 `AsyncSession.execute()` 调用方式不一致：测试错误地链式配置 `db.execute.return_value.scalar_one.return_value`，而生产代码会先 `await db.execute(...)` 再调用结果对象的 `scalar_one()`。

已将测试改为配置 awaited result，并增加 `db.execute.assert_awaited_once()` 断言。该修复只调整测试 double，不改变生产实现。

## 验收要求

按既有测试职责隔离执行：

1. backend `uv run pytest -q`；
2. backend migration gate `scripts/migration/01_migrate.ps1`；
3. backend real API gate `scripts/test/api-real/01_run_real_api_tests.ps1`；
4. frontend `npm test`；
5. frontend `npm run build`；
6. 最后进行手工验证：失败 Execution Retry、pending/running Execution Cancel、Audit/Trace 查询以及 tenant/RBAC 边界。

不新增重复测试入口，不把开发脚本与测试脚本混用。

## 下一步

进入 Execution 治理前端闭环：在 Runtime Execution 详情中展示 Retry / Cancel 操作状态、Retry 血缘关系和治理结果，并保持现有 API、权限和 Trace 数据模型复用原则。
