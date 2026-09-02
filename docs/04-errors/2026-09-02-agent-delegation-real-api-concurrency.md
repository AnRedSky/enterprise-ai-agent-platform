# Agent Delegation Real API 并发验收失败记录

## 1. 发现时间

2026-09-02。

## 2. 本地实际结果

Tenant Safe Real API Gate 在最新 `main` 基线 `6b41c4828fbb375af1f9570f9216d09b4da91f3d` 上实际执行：

- Backend regression：`1042 passed, 3 skipped, 79 deselected`
- Migration/head：通过，当前 head 为 `0056_merge_legacy_audit_and_operator_governance_heads`
- Real API：`74 passed, 1 skipped, 2 deselected`
- 失败：B4 timeout、B2 worker bridge、B6 multi-worker 各 1 个

## 3. 根因分析

### B4 timeout

测试先创建 Delegation，再在独立事务中执行 Claim。项目明确允许后台 Worker 并发运行，因此后台 Worker 可以在测试 Claim 前取得同一 Delegation 的 row lock 并完成 Claim，测试随后收到 `409 Delegation 当前状态为 running`。

根因不是 Delegation 状态机错误，而是测试 Fixture 的 `pending → claim` 观察窗口没有建立数据库并发屏障。

修复：B4 在 Claim 前对目标 Delegation 执行 `SELECT ... FOR UPDATE`，随后在同一 Session 调用正式 `claim_delegation()`，确保当前测试先形成确定 generation。

### B6 multi-worker

原测试逐条创建 Mock Provider/Profile，并由 helper 每条单独 commit。已有后台 Worker 可以在某个 Profile 尚未装配完成时先 Claim Delegation，随后 Runtime Bridge 缺少完整 Model Profile 上下文而将该 Delegation 收敛为 `failed`。

根因是测试 Fixture 把“任务可被 Worker Claim”和“Runtime 依赖已经完整装配”拆成多个 commit。

修复：B6 一次性锁住全部 Delegation，并在同一事务内完成全部 Target Agent Version / Delegation 的 Mock Profile 装配，最后统一 commit，再允许 Worker 竞争。

### B2 worker bridge

B2 仍存在相同类别的后台 Worker Claim 竞态：测试在 HTTP 创建 Delegation 后才建立确定性 Mock Profile，然后要求测试 Worker 自己通过 Delegation discovery 入口取得该任务。若外部后台 Worker 在此期间先 Claim，测试 Worker 合法返回 `None`，但原断言把“必须由本测试 Worker 取得 Claim”误当成业务 Contract。

该问题属于测试并发隔离策略，不能通过放宽 Worker fencing 或允许其他 Worker 的 Execution 被当前 Worker 接管来修复；后续应将 B2 Fixture 的 Profile 装配与 Claim 观察窗口改造成确定性的数据库锁/原子 Fixture，或者增加正式的已 Claim Frontier 验证入口，而不修改生产 ownership Contract。

## 4. 设计约束

- 不关闭、重启或接管已有 Worker/Scheduler。
- 不降低 Worker fencing 要求。
- 不允许测试通过固定 owner 假设后台 Worker 不存在。
- 不复制生产 Runtime 算法到测试。
- 测试 Fixture 必须在 Worker 可观察之前一次性达到完整、可执行状态。

## 5. 后续验收

完成 B2 Fixture 并发屏障后，重新执行：

```powershell
cd backend
uv run pytest -q -W error `
  tests/api_real/test_agent_delegation_bridge_api.py `
  tests/api_real/test_agent_delegation_b4_api.py `
  tests/api_real/test_agent_delegation_multi_worker_api.py `
  -m real_api
```

随后执行完整 Backend Regression Gate。Real API 只有在本地实际达到全通过后，才允许将本轮 Backend Gate 标记为通过。
