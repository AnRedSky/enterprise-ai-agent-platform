# ERR-0015 — Circuit Breaker Policy / HALF_OPEN Probe 治理

- Legacy ID: `011-circuit-breaker-policy-and-half-open-probe-governance`
- Phase: 1.5-G

同一 `tenant_id + circuit_key` 不同 Workflow 可携带不同 recovery policy，原实现从当前 Workflow config 决定 OPEN→HALF_OPEN；同时 probe reservation 未在成功预约后提交释放锁。修复为持久化 `failure_threshold/recovery_timeout_ms/half_open_max_calls`，migration `0021`，policy drift=409，事务内原子预约 probe slot 并释放锁；Real API 使用一致 policy 并验证并发 probe quota。
