# 011 Circuit Breaker Policy 与 HALF_OPEN Probe 治理修正

## 1. 实际错误

Phase 1.5-G Real API 验收发现，同一个 `tenant_id + circuit_key` 的不同 Workflow 可以携带不同 `recovery_timeout_ms` / `half_open_max_calls` 配置；原实现直接使用当前调用的 Workflow 配置决定 OPEN → HALF_OPEN，导致 Circuit 的恢复语义不属于持久化 Circuit State 本身。

同时，HALF_OPEN probe 配额虽然使用数据库行锁，但 probe provider 调用期间没有在预约后释放锁，无法对并发 probe quota 做明确的独立验收。

## 2. 根因

1. Circuit State 只持久化状态和计数，没有持久化治理 policy。
2. OPEN / HALF_OPEN 状态转换重新读取当前 Workflow config。
3. HALF_OPEN probe slot reservation 仅 flush，没有在 reservation 成功后提交并释放行锁。
4. Real API fixture 使用不同 recovery policy 验证恢复，反而暴露了 policy ownership 不明确的问题。

## 3. 影响

- 相同 Circuit Key 可能出现不一致的 recovery timeout。
- 不同 Workflow 可能静默改变已有 Circuit 的 HALF_OPEN quota。
- 并发 HALF_OPEN probe 的治理边界缺少独立 Real API 验收。
- OPEN Fast-Fail 的 `attempt=1` 结果可能受到 recovery timeout 到期时机影响。

## 4. 修复

1. `workflow_circuit_states` 增加并持久化：
   - `failure_threshold`
   - `recovery_timeout_ms`
   - `half_open_max_calls`
2. 新增 Alembic `0021_workflow_circuit_policy`。
3. 已存在的 Circuit Key 必须严格匹配持久化 policy；policy drift 返回 HTTP 409。
4. OPEN → HALF_OPEN 时原子预约 probe slot，并提交事务释放行锁。
5. HALF_OPEN quota 使用持久化 `half_open_max_calls` 判断。
6. Real API 使用相同 Circuit Policy，并增加两个并发 HALF_OPEN probe 的真实 HTTP 验收。
7. 增加 deterministic `mock-slow-success` provider，避免并发 probe 测试依赖外部 Provider。

## 5. 预防

- Circuit state 与 Circuit policy 必须属于同一持久化治理对象。
- Real API fixture 不得通过不同 Workflow config 绕过 Circuit policy ownership。
- HALF_OPEN 并发 quota 必须至少有一次真实 HTTP 并发验收。
- OPEN Fast-Fail 必须同时验证 HTTP 503、`CIRCUIT_OPEN`、Node attempt=1、无 retry scheduled。

## 6. 验证要求

开发者本地必须依次执行：

```powershell
cd backend
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

其中 Real API 必须验证 CLOSED / OPEN / HALF_OPEN、policy persistence、policy drift、并发 probe quota、success recovery、failure reopen、Retry / Timeout / Governance 边界。
