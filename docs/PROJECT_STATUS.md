# Project Status

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：进行中。
- 2.2-A Contract：已形成。
- 2.2-B Dataset / Runner：本轮最新 main 已由开发者本地实际验证通过；Backend regression 与 Real HTTP API gate 均通过。
- 2.2-C Real Provider Quality Gate：baseline 已冻结；本轮最新 main 已由开发者本地实际验证通过，Recall@3 / Precision@3 / MRR 均恢复 baseline，provider error rate=0。
- 2.2-D Retrieval Quality Regression：citation correctness 的真实 Runtime evidence bridge 已实现；evaluation run / case / regression result 已持久化到现有 Runtime Observability / Audit 模型，并已增加 trace persistence / API contract 自动化覆盖，待开发者本地重新执行验证。

## 本轮实际验证基线

```text
Backend default regression: 309 passed, 30 deselected
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
7. Standalone trace runner 的 workflow / execution / audit 外键模型依赖已注册，并增加 clean-process bootstrap 回归测试。
8. 新增 Runtime trace API contract 测试，并新增 Real API traceability 测试：执行真实 Provider runner 后，通过真实 HTTP API 验证 execution、case、summary 与对应 audit 记录可追踪。

## 下一步

1. 开发者本地执行新增 `test_api_runtime_endpoints.py` 与 `test_retrieval_evaluation_trace_api.py`，确认 trace persistence / API contract 自动化覆盖通过。
2. 重新执行 Backend regression、migration/head 与 Real API gate，确认新增 trace 测试没有破坏现有系统。
3. 手工执行 Real Provider runner 后，用其输出的 `evaluation_run_id` 调用 Retrieval Evaluation Trace API，并检查对应 Audit Log。
4. 保持 Backend / Frontend / Browser Gate 独立；未实际执行的 Gate 不得标记 Passed。
5. Provider / model / dimension / dataset / retrieval mode / top-k 变化继续执行 baseline regression；禁止通过修改 baseline 掩盖回归。
