# Phase 2.3 Acceptance

## 当前验收状态

- Phase：2.3 Model Provider Governance
- 2.3-A Contract：已实现并验收
- 2.3-B Backend Domain + API Contract：已实现并验收
- 2.3-C Runtime Governance Invocation：已实现并验收
- 2.3-D Runtime Usage / Trace Identity：已实现并验收
- **2.3-E Governed fallback success：Passed**
- **2.3-F Fallback Policy Enforcement：Passed**
- **2.3-G Cost / Usage Accounting：Passed**
- **Phase 2.3：已正式关闭**

## 2.3-G 实际验收证据

开发者在最新 `main`（`14fd450`）实际执行：

```text
2.3-G targeted tests: 40 passed
Backend default regression: 358 passed, 35 deselected
Alembic upgrade heads: passed
Alembic current: 0023_model_usage_accounting (head), 0027_retrieval_evaluation_vector_space (head)
Tenant Safe Real API Gate: 35 passed
```

上述结果均为开发者本地实际执行结果，不以 GitHub Actions 作为验收依据。

## 2.3-G 验收范围

1. `model_usage_records` PostgreSQL 持久化表；
2. 每个 governed provider attempt 一条 durable usage record；
3. 成功、失败、fallback attempt 均保留 request unit；
4. prompt/completion/total token usage 可持久化；
5. pricing source/version 与 input/output/request rate 可追溯；
6. request/token cost 使用确定性计算；
7. `GET /api/v1/usage/model` 支持 organization scoped 查询与 execution 过滤；
8. active organization membership 越权访问被拒绝；
9. usage 与 `model.invocation` trace 保持同事务持久化；
10. endpoint、credential_ref、Token、Secret 不进入 usage/audit/trace。

## Phase 2.3 关闭结论

2.3-G Gate 全部通过，且 2.3-A 至 2.3-F 已完成对应验收，因此 Phase 2.3 正式关闭。

当前不继续扩张未经产品确认的 Provider Governance UI、Browser E2E 或其他 Provider 能力。下一阶段为候选 Phase 2.4 Durable Scheduler，必须先确认 scheduler Contract 后才能转化为代码任务。
