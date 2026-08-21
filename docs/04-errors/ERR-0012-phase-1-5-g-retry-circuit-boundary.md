# ERR-0012 — Phase 1.5-G Retry / Circuit Boundary 验收失败

- Legacy ID: `008-phase-1-5-g-real-api-retry-and-circuit-boundary`
- Phase: 1.5-G

历史 Real API / pytest 暴露三项：terminal Execution 后原始 ConnectionError 被包装为 HTTP 500；Retry Audit 缺少兼容动作 `workflow.node.retry`；独立 Execution 的 `CIRCUIT_OPEN` 首节点 attempt 观测为 2。修复 commit `e0fff63ca6fdd56cb40bd7bb03f28b779b34d7a3` 显式设置新 Node Execution `attempt=1`、同时记录 retry audit 兼容动作，并避免 terminal state 后二次包装原始异常。要求真实 pytest / Real API / migration 复测。
