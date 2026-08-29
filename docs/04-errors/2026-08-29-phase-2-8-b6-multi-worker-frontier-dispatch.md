# Phase 2.8 B6 多 Worker Durable Frontier 验收失败

## 1. 现象

开发者在远端 `main` 基线 `16020f68` 执行 B6 Gate：

```text
Delegation Claim + Worker dispatch Unit/Contract   29 passed
Backend regression                                  861 passed, 3 skipped, 51 deselected
Migration/head                                     0039_workflow_node_execution_tenant_trigger (head)
Real HTTP + PostgreSQL multi-worker Runtime        3 passed, 2 failed
```

失败一：4 个 Delegation 只形成 2 个 Worker dispatch 事实：

```text
first_round  = [1, 1]
second_round = [0, 0]
assert 2 == 4
```

失败二：B2 Target Agent Runtime 直接执行时，Execution terminalization 被活动 Frontier fencing 拒绝：

```text
HTTP 409: Execution 仍存在活动 Frontier，不允许直接进入 terminal 状态
```

## 2. 根因

### 2.1 Delegation Claim 与 Frontier 二次全局发现之间存在空转窗口

B6 初始 Worker 流程为：

```text
claim_one_frontier()
  ↓ 无普通 Frontier
claim_one_pending_delegation()
  ↓ claim_delegation() 已提交 Execution + Frontier
claim_one_frontier()
  ↓ 再次通过 tenant candidate 全局扫描寻找 Frontier
```

`claim_delegation()` 已经完成事务提交，但随后重新扫描 Frontier 并不是本次 Claim 的确定性 continuation。并发 Worker、候选排序、lease 状态变化都可能改变下一次扫描结果，使当前 dispatch 出现“Delegation 已 Claim、但本轮没有拿到对应 Frontier”的空转。该问题违反 Worker work item 链路应由稳定 identity 贯通的原则。

### 2.2 B2 Real API 测试绕过了 B6 正式 Durable Frontier 边界

B2 测试直接调用 `execute_claimed_execution()`。B6 已将 Frontier 作为 Worker 的正式 durable work item，并通过 Execution → Frontier terminalization fencing 阻止出现 `terminal Execution + active Frontier` 的分叉状态。

因此旧测试路径不再代表生产 Worker 合法执行路径：Runtime terminalization 前仍存在 active Frontier，返回 409 是正确的 fail-closed 行为，而不是应该放宽 fencing 的生产缺陷。

## 3. 修复

1. 新增 Worker 内部确定性 `pending Delegation → Frontier` 激活路径：使用 `claim_delegation()` 返回的 `worker_execution_id` 直接定位刚创建的 Frontier，再建立当前 Worker 的 Frontier lease。
2. `dispatch_once()` 在没有普通 Frontier 时直接消费上述 Claim 返回的 Frontier，不再执行第二次全局 tenant Frontier 扫描。
3. 保留原有 `claim_one_pending_delegation()` 布尔入口，避免破坏已有 Worker 调用契约。
4. B2 Real API 验收改为 `WorkflowWorker.claim_one_frontier()` + `execute_frontier()`，通过正式 Durable Frontier Worker 路径验证 Target Agent Runtime。
5. 不放宽 Execution terminalization fencing，不允许通过删除 active Frontier 保护来“修测试”。

## 4. 边界与验证

- 不新增队列系统；
- 不新增第二套 Retry / Recovery 状态机；
- 不改变 Delegation tenant、generation、timeout、audit/trace 语义；
- 不新增数据库 migration；
- 修复后必须重新执行 B6 Real Gate，并重新执行 Backend default regression。
