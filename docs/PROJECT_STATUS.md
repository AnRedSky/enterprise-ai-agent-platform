# Project Status

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：进行中。
- 2.2-A Contract：已形成。
- 2.2-B Dataset / Runner：已完成既有交付范围，并已由开发者本轮实际执行验证。
- 2.2-C Real Provider Quality Gate：已通过当前 main 的真实 Provider baseline regression。
- 2.2-D Retrieval Quality Regression / Traceability：代码、持久化、API contract 与 Real API traceability 已完成当前定义范围，并已由开发者本轮实际验证通过。
- 当前新增工作：将 Real Provider 检索模型与评估参数从 runner 内部固定值提升为显式、可覆盖的 evaluation configuration；本次变更不修改冻结 baseline。

## 当前 main 基线

远端 `main` 已包含提交 `175c5cf`（`docs(retrieval): record 2.2 traceability gate verification`）。本次开发必须以该最新 `main` 为基线；不得继续以更早的 `2559884` 作为开发基线。

## 已验证基线

以下均为开发者此前在当前 main `2559884` 之后实际执行反馈，并已记录到本项目文档；本次配置化变更尚未声称这些结果是本轮重新执行：

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

## 本轮开发目标

1. 检索 Embedding Provider、model、endpoint、dimension、timeout 不应只能依赖后端固定实现；evaluation runner 必须允许单次运行显式覆盖。
2. Dataset、fixture、baseline 路径应可显式指定，避免评估语义被代码内固定路径锁死。
3. `top_k`、`min_score`、Recall@K / Precision@K / MRR / Citation correctness 最低阈值、provider 最大错误率必须允许评估任务自定义。
4. API key 只能通过环境变量名引用，不能进入命令行参数值、评估报告或 Git。
5. 配置必须进入 evaluation trace metadata，使结果可审计、可复现；baseline identity 继续只由既有 Provider / model / dimension / dataset / retrieval mode / top-k 字段决定，不得通过修改阈值掩盖 regression。
6. 线上 Runtime 默认仍使用 `settings`；evaluation runner 通过显式 provider injection 执行，不修改全局运行配置。

## 下一步

1. 在最新 main 上完成上述 evaluation configuration 实现与单元测试。
2. 本地执行配置化单元测试、Real API Gate、Real Provider runner 与 Backend Regression Gate；只记录实际执行结果。
3. 使用至少一组与当前冻结 baseline 不同的 model/provider 或评估参数做一次配置解析/运行验证；若 identity 发生变化，不得覆盖现有 baseline，应使用独立 baseline 文件或明确记录 identity change。
4. 对当前 Recall@3=0.6、Precision@3=0.333333、citation_correctness=0.333333 做产品质量结论评估；不得通过修改 baseline 掩盖指标。
5. 若产品要求更高真实语义质量，应先形成明确质量目标与架构/方案决策，再决定是否继续在 Phase 2.2 内迭代；不得直接创建未经立项的 Phase 2.3。
6. Frontend / Browser Gate 保持独立，未实际执行不得标记 Passed。
