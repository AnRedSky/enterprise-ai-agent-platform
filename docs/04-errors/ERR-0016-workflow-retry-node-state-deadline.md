# ERR-0016 — Workflow Retry Node State / Deadline Boundary

- Legacy ID: `012-workflow-retry-node-state-and-deadline-boundary`

Retry 第一次失败后下一次 attempt 未显式 `failed -> running`，真实 DB 状态机可能出现 `failed -> failed`；retry backoff 跨越 Workflow deadline 时仍记录 scheduled 而未 exhausted。修复为 retry sleep 后显式 transition `running`，在记录 scheduled 前比较剩余 deadline，`delay >= remaining` 时记录 `node.retry.exhausted` / `workflow_deadline` 并以 `WORKFLOW_TIMEOUT` 结束。增加 retry transition unit contract，并要求 Real API 验证。
