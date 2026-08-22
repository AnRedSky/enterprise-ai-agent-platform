# Project Status

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：进行中。
- 2.2-A Contract：已形成。
- 2.2-B Dataset / Runner：本轮最新 main 已由开发者本地实际验证通过；Backend regression 与 Real HTTP API gate 均通过。
- 2.2-C Real Provider Quality Gate：baseline 已冻结；本轮最新 main 已由开发者本地实际验证通过，Recall@3 / Precision@3 / MRR 均恢复 baseline，provider error rate=0。
- 2.2-D Retrieval Quality Regression：citation correctness 的真实 Runtime evidence bridge 已实现；本轮继续实现 evaluation run / case / regression result 到现有 Runtime Observability / Audit 模型的持久化追踪。

## 本轮实际验证基线

```text
Backend default regression: 308 passed, 30 deselected
Migration head: 0024_embedding_dimension_contract
Real HTTP API: 30 passed

Real Provider runner:
  provider=ollama
  model=nomic-embed-text:latest
  embedding_dimension=768
  cases=5
  provider_error_rate=0
  recall@3=0.6
  precision@3=0.333333
  mrr=0.6
  citation_correctness=0.333333
  quality_gate=passed
```

既有冻结 baseline 仍为 Recall@3=0.6、Precision@3=0.333333、MRR=0.6。本轮没有重新冻结 baseline。

## 本轮完成

1. Scheduled Trigger Real API test 等待 execution terminal state，消除 durable claim 与 runtime completion 之间的时序竞态。
2. Scheduled Trigger 双 worker convergence test 显式限制为一个 slot，避免把 recovery dispatch 混入单 slot idempotency 断言。
3. Retrieval evaluation fixture 改为使用正式 Runtime Retrieval 所要求的 `ready` document-version / ingestion 状态，再由 runner 将 vector index 状态推进到 `ready`。
4. Real Provider Quality Gate 已由开发者本地重新验证通过，恢复冻结 baseline contract。
5. Evaluation runner 现在将 evaluation run、每个 case、summary regression、provider/model/dimension/dataset/retrieval identity 持久化为现有 `executions` / `execution_events`，并写入 `audit_logs`。
6. 新增 admin-only `/api/v1/runtime/retrieval-evaluations/{evaluation_run_id}` 查询入口，复用现有 Runtime Observability timeline 查询模型。

## 下一步

1. 本轮 Traceability persistence 代码需由开发者本地执行 Backend regression、migration/head 与 Real API gate，确认新增持久化链路没有破坏现有系统。
2. 手工执行 Real Provider runner 后，用其输出的 `evaluation_run_id` 调用 Retrieval Evaluation Trace API，确认数据库中存在 run、case、summary 与 audit 记录。
3. 增加针对 trace persistence / API contract 的自动化测试，并在真实 API Gate 中覆盖。
4. 保持 Backend / Frontend / Browser Gate 独立；未实际执行的 Gate 不得标记 Passed。
5. Provider / model / dimension / dataset / retrieval mode / top-k 变化继续执行 baseline regression；禁止通过修改 baseline 掩盖回归。
