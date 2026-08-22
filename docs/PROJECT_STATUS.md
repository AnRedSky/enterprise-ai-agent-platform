# Project Status

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：进行中。
- 2.2-A Contract：已形成。
- 2.2-B Dataset / Runner：代码修复完成；此前本地 Gate 已通过，但最新 main 上真实 Runtime hydration contract 暴露 fixture 状态不一致问题，本轮修复后需重新执行。
- 2.2-C Real Provider Quality Gate：baseline 已冻结；最新 main 的 runner 曾因 fixture hydration 状态不一致出现 Recall@3=0 / MRR=0，本轮已修复但尚未重新由开发者本地验证。
- 2.2-D Retrieval Quality Regression：citation correctness 的真实 Runtime evidence bridge 已实现；当前继续推进 Retrieval Debug / Audit / Observability 持久化追踪。

## 本轮实际验证基线

```text
Ollama embedding smoke: PASS（开发者此前实际执行）
  provider=ollama
  model=nomic-embed-text:latest
  dimension=768
  vector_count=1

此前最新 main Gate 反馈：
Backend default regression: 308 passed, 30 deselected
Migration head: 0024_embedding_dimension_contract
Real HTTP API: 28 passed, 2 failed
  - scheduled execution was observed in pending state before terminal completion
  - two-worker scheduled test counted current + recovery dispatches together

此前最新 main Real Provider runner：
  provider=ollama
  model=nomic-embed-text:latest
  embedding_dimension=768
  cases=5
  provider_error_rate=0
  recall@3=0.0
  precision@3=0.0
  mrr=0.0
  quality_gate=failed

修复后的结果尚未由开发者本地实际执行，不得标记为 Passed。
```

此前冻结的真实 baseline 仍为：Recall@3=0.6、Precision@3=0.333333、MRR=0.6。该 baseline 不得因本次 fixture 修复而重写；修复后应验证当前结果是否恢复到 baseline contract。

## 本轮修复单元

1. Scheduled Trigger Real API test 等待 execution terminal state，消除 durable claim 与 runtime completion 之间的时序竞态。
2. Scheduled Trigger 双 worker convergence test 显式限制为一个 slot，避免把 recovery dispatch 混入单 slot idempotency 断言。
3. Retrieval evaluation fixture 改为使用正式 Runtime Retrieval 所要求的 `ready` document-version / ingestion 状态，再由 runner 将 vector index 状态推进到 `ready`。
4. 工程错误记录新增 `ERR-0021`，保留本轮真实失败证据与修复边界。

## 下一步

1. 先由开发者本地重新执行 Backend default regression、Migration/head、Real HTTP API 与 Real Provider Quality Gate，确认本轮修复真实恢复。
2. Gate 恢复后继续 Phase 2.2-D：把 evaluation run / case / provider / dataset / regression result 接入现有 Retrieval Debug / Audit / Observability 查询模型。
3. 保持 Backend / Frontend / Browser Gate 独立；未实际执行的 Gate 不得标记 Passed。
4. Provider / model / dimension / dataset / retrieval mode / top-k 变化继续执行 baseline regression；禁止通过修改 baseline 掩盖回归。
