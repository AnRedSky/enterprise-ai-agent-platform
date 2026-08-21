# ERR-0005 — Circuit Breaker 新建状态计数初始化

- Legacy ID: `003-circuit-breaker-state-initialization`
- Phase: 1.5-G

首次 `record_failure()` 创建 ORM state 后在 flush 前读取 `failure_count`，可能得到 `None`，导致 `TypeError` 并使 Real API OPEN 场景返回 500。根因是错误依赖 DB/ORM default 的 flush 后回填。修复为显式初始化 `failure_count`、`success_count`、`state`，并增加首次 failure / state transition / Real API 回归。原记录要求真实 PostgreSQL 验证，不以 mock 代替。
