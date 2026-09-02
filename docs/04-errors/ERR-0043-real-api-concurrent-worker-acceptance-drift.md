# ERR-0043 Real API 并发 Worker 验收环境漂移

## 现象

Tenant Safe Real API Gate 在允许多个 Worker 并发运行的开发者环境中出现以下失败：

- Operator Action 真实验收清理用户时，`operator_action_idempotencies.actor_id` 的 `RESTRICT` 外键阻止删除用户；
- Canonical Operator Audit 索引验收通过 `pg_indexes.indexdef` 的双引号文本判断列存在，PostgreSQL 实际生成的普通标识符 DDL 可能不带双引号，导致 schema 正确但断言失败；
- Agent Delegation B2/B3 与多 Worker 验收把“必须由当前测试进程 Claim”作为隐含前提，而 Gate 明确允许已有 Worker 并发消费测试数据，导致测试与服务并发语义冲突；
- B4 timeout 验收在绑定 Model Profile 后再 Claim，扩大了 pending 状态的竞态窗口，后台 Worker 可以在测试 Worker Claim 前先取得 Delegation；
- Multi Worker 验收要求当前测试进程的 owner 必须出现在 Claim owner 集合中，即使后台 Worker 合法取得全部任务也会误报失败。

## 根因

### 1. Operator Action 测试清理顺序错误

`OperatorActionIdempotency.actor_id -> users.id` 使用 `ON DELETE RESTRICT`。测试先删除 User，再删除幂等事实，真实 PostgreSQL 会正确拒绝删除。

修复方式：在删除 User 前按 actor_id 清理 `OperatorActionIdempotency`。

### 2. 索引验收依赖展示文本格式

`pg_indexes.indexdef` 是 PostgreSQL 生成的索引 DDL 展示文本，不应作为列元数据的唯一事实来源。索引的逻辑列集合由 `pg_index.indkey` 表达，并通过 `pg_attribute.attname` 映射到真实列名。

修复方式：验收直接读取 PostgreSQL system catalog 的实际索引列顺序，避免引用格式差异造成误报。

### 3. Real API Gate 的 Worker 并发边界未落实到 Delegation 验收

Gate 不创建、停止或隔离 Worker，并明确允许多个 Worker 同时执行。Delegation 测试却隐含要求当前测试进程一定能获得 Claim，造成后台 Worker 正常抢占时出现 409、None 或 owner 断言失败。

修复原则：

- B2/B3 使用实际持久化的 Worker Execution / Frontier 与 generation 事实进行验收，不把测试进程 owner 视为业务契约；
- B4 timeout 在 Claim 前不需要 Model Profile，因为 Runtime timeout 判断发生在真正执行 Target Agent 之前。因此测试先 Claim，再设置已到期 timeout，消除不必要的 pending 竞态窗口；
- Multi Worker 验收允许外部 Worker 参与全部 Claim，只要求每个 Delegation 恰好形成一个 Claim Audit、一个 Worker Execution 和一个 Durable Frontier，并最终完成；
- 并发测试同时让两个独立测试 Worker 进入正式 Delegation discovery 入口，但不把某个 Worker 是否实际抢到任务作为固定结果。

## 禁止的错误修复

- 不通过忽略 `-W error` 绕过失败；
- 不通过停止或重启 Worker/Scheduler 消除并发；
- 不通过固定手工 ID、Token 或测试数据规避竞态；
- 不修改生产 tenant boundary、幂等或 Claim 原子语义来迎合测试。

## 验证

必须由开发者本地执行并反馈实际结果：

```powershell
cd backend

uv run pytest -q -W error `
  tests/api_real/test_operator_action_execution_acceptance.py `
  tests/api_real/test_batch_operator_actions_acceptance.py `
  tests/api_real/test_operator_audit_query_indexes_acceptance.py `
  -m real_api

uv run pytest -q -W error `
  tests/api_real/test_agent_delegation_bridge_api.py `
  tests/api_real/test_agent_delegation_b4_api.py `
  tests/api_real/test_agent_delegation_multi_worker_api.py `
  -m real_api

powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\release\01_backend_regression_gate.ps1
```

以上命令不启动、重启或停止 API、Worker、Scheduler、PostgreSQL、Redis；依赖服务必须已经由开发环境提供。测试上下文由 Real API Gate 自动生成，不要求手工填写测试 ID、Token 或业务数据。

## 状态

本次开发者反馈暴露的 B4 与 Multi Worker 验收竞态已完成代码修复；最终通过状态必须以开发者重新执行上述 Real API / Backend Gate 的实际结果为准。
