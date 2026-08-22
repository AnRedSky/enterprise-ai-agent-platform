# Project Status

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：进行中。
- 2.2-A Contract：已形成。
- 2.2-B Dataset / Runner：已完成既有交付范围。
- 2.2-C Real Provider Quality Gate：baseline 已根据开发者实际反馈恢复并固化到仓库；本次提交后尚待重新执行 Gate 验证。
- 2.2-D Retrieval Quality Regression：citation correctness 的真实 Runtime evidence bridge 已实现；evaluation run / case / regression result 已持久化到现有 Runtime Observability / Audit 模型，并已增加 trace persistence / API contract 自动化覆盖；本轮 Real API gate 当前被 baseline 缺失阻塞，baseline 已在本提交中补齐。

## 本轮实际验证基线

以下是开发者本轮反馈的实际结果，不表示本提交后的重新验证结果：

```text
Backend default regression: 309 passed, 31 deselected
Migration head: 0024_embedding_dimension_contract
Real HTTP API: 30 passed, 1 failed

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
  quality_gate=failed (baseline missing)
```

冻结 baseline 为 Recall@3=0.6、Precision@3=0.333333、MRR=0.6，provider/model/dimension/dataset/retrieval/top-k identity 已固化。此次提交没有修改质量指标以掩盖回归。

## 本轮完成

1. Real API admin fixture 已修复为可在 `uv run` 环境下导入项目 `app` 包；Real API gate 已能进入真实 HTTP 测试阶段。
2. 新增 Retrieval evaluation trace 的 admin fixture / contract / persistence 覆盖后，发现 Real Provider baseline 文件未随当前 main 固化，导致 runner 在 trace API 调用前失败。
3. 根据开发者实际 Real Provider runner 输出，将冻结 baseline 固化到 `backend/evaluation/knowledge_retrieval_real_baseline.json`。
4. 按开发准则新增 `ERR-0022`，记录 baseline 缺失、影响、修复与验证边界。
5. 保持 baseline regression 的 identity 检查和显式 freeze 规则，不自动通过质量 Gate。

## 下一步

1. 在最新 main 上执行 `uv run pytest -q tests/api_contract/test_api_runtime_endpoints.py` 与 Retrieval trace API 相关测试。
2. 重新执行 Backend Release / Regression Gate，确认 baseline 固化后 Real HTTP API 全部通过。
3. 手工执行 Real Provider runner，确认输出为 `quality_gate=passed`，并用 `evaluation_run_id` 调用 Retrieval Evaluation Trace API 检查 execution、case、summary 与 Audit Log。
4. 保持 Backend / Frontend / Browser Gate 独立；未实际执行的 Gate 不得标记 Passed。
5. Provider / model / dimension / dataset / retrieval mode / top-k 变化继续执行 baseline regression；禁止通过修改 baseline 掩盖回归。
