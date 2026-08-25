# Browser E2E：Organization / Tenant 隔离导致场景互相污染

## 1. 现象

2026-08-25 本地 Browser E2E 执行出现以下失败：

- Organization 创建接口返回 `409`；
- Organization member 创建返回 `422`；
- owner transfer 依赖的 Organization 状态不满足；
- Model Provider/Profile E2E 因 Organization 创建失败而连锁失败。

## 2. 根因

当前 Organization 领域明确保持“一 Tenant 一 Organization”约束。注册接口中的本地 E2E 用户默认进入同一个 Tenant，因此不同 Playwright 场景虽然使用随机用户名和 Organization 名称，仍然竞争同一个 Tenant 的 Organization 根聚合。

原 Browser E2E Gate 直接并行执行多个场景，并且没有在场景之间清理 Organization 根聚合，因此前一个场景创建的数据会阻塞后一个场景。该问题属于测试隔离设计错误，不应通过放宽生产 Organization 领域约束解决。

## 3. 修复

1. 新增 `backend/scripts/test/e2e/00_reset_browser_e2e_database.py`，仅用于本地 Browser E2E 场景隔离，通过 PostgreSQL `TRUNCATE TABLE organizations CASCADE` 清理 Organization 根聚合及其级联测试数据。
2. 新增 `frontend/scripts/test/e2e/00_run_isolated_test.ps1`，每个 Browser 场景执行前自动完成数据库隔离，再运行真实 Browser -> Vue -> Backend HTTP 链路。
3. Organization Browser Gate 改为逐场景隔离执行。
4. Workflow Trigger Browser Gate 不再误执行其他领域 E2E，只执行 Scheduler 对应场景。
5. Model Provider/Profile Browser Gate 独立为单独入口，并同样采用场景隔离。

## 4. 边界

该清理工具只能用于本地 Browser E2E 测试数据库，不得用于生产数据库，不替代 Alembic migration，也不改变生产 Organization / Tenant 业务规则。

## 5. 后续验证

开发者本地需要重新执行对应 Browser E2E Gate，只有实际执行结果通过后，才能更新 Phase / Acceptance 为 Passed。
