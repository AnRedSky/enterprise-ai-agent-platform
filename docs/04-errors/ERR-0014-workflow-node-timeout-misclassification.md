# ERR-0014 — Workflow Node Timeout 被错误分类

- Legacy ID: `010-workflow-node-timeout-misclassification`

Backend 回归曾出现 Node timeout 期望 `NODE_TIMEOUT`、实际 `WORKFLOW_TIMEOUT`。根因是用 `effective_timeout=min(node_timeout, remaining)` 的结果反推 timeout 来源，丢失了预算来源语义。修复为直接比较 `remaining <= node_timeout_ms/1000`。要求分别覆盖 NODE_TIMEOUT / WORKFLOW_TIMEOUT，并重新执行 Backend regression。
