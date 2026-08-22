# Project Status

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：进行中。
- 2.2-A Contract：已形成。
- 2.2-B Dataset / Runner：已完成既有交付范围，并已由开发者本轮实际执行验证。
- 2.2-C Real Provider Quality Gate：已通过当前 main 的真实 Provider baseline regression。
- 2.2-D Retrieval Quality Regression / Traceability：代码、持久化、API contract 与 Real API traceability 已完成当前定义范围，并已由开发者本轮实际验证通过。

## 本轮实际验证结果

以下均为开发者在当前 main `2559884` 之后实际反馈的结果：

```text
Real HTTP API: 31 passed
API Runtime Contract: 2 passed
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
Backend regression gate:
  Backend regression: 309 passed, 31 deselected
  Migration head: 0024_embedding_dimension_contract
  Real HTTP API: 31 passed
  Backend regression gate: passed
```

Real Provider regression 与冻结 baseline 一致：Recall@3=0.6、Precision@3=0.333333、MRR=0.6，identity 未发生变化，provider error rate=0。

注意：`uv run pytest -q tests/api_real/test_retrieval_evaluation_trace_api.py` 单独执行时由于 Real API marker 默认被 deselect，不能作为 Real API trace 验收结果；本轮完整 `01_run_real_api_tests.ps1` 已实际执行并通过 31 个 Real HTTP API tests。

## 本轮完成

1. 修复 Real API admin fixture 的项目包导入问题，使真实 HTTP gate 可进入完整测试阶段。
2. 修复并固化 Real Provider baseline，恢复 baseline regression gate。
3. 新增 Retrieval evaluation trace persistence / API contract / Real API traceability 覆盖，并确认真实 runner 产生的 `evaluation_run_id` 可进入 Runtime Observability / Audit 查询链路。
4. 开发者本轮实际执行完整 Real API gate，结果为 `31 passed`。
5. 开发者本轮实际执行 Backend Release / Regression Gate，结果为 `309 passed, 31 deselected`、migration head `0024_embedding_dimension_contract`、Real API `31 passed`。
6. 保持 Backend / Frontend / Browser Gate 独立，不以未执行的 Gate 作为验收证据。

## 当前结论

2.2-D 当前定义的 traceability 自动化与 Real API 验收已经具备实际通过证据。Phase 2.2 尚不应仅因 baseline regression 通过而自动关闭；当前真实 Provider 指标仅代表冻结回归基线，并不等同于产品语义质量已经达到最终目标。

## 下一步

1. 完成 2.2-D Acceptance 文档与 Project Status 的本轮实际结果固化。
2. 对当前 `recall@3=0.6`、`precision@3=0.333333`、`citation_correctness=0.333333` 做产品质量结论评估；不得通过修改 baseline 掩盖指标。
3. 若产品要求更高真实语义质量，应先形成明确质量目标与架构/方案决策，再决定是否继续在 Phase 2.2 内迭代；不得直接创建未经立项的 Phase 2.3。
4. 后续 Provider / model / dimension / dataset / retrieval mode / top-k identity 变化继续执行 baseline regression。
5. Frontend / Browser Gate 保持独立，未实际执行不得标记 Passed。
