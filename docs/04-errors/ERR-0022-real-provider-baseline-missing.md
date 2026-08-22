# ERR-0022 — Real Provider baseline 缺失导致 Real API trace gate 阻塞

## 现象

在 `main` 的 Retrieval evaluation trace 已接入 Real API gate 后，真实 Provider runner 能完成 5 个 case，但因为 `backend/evaluation/knowledge_retrieval_real_baseline.json` 不存在，runner 返回非零状态；因此 `test_real_provider_evaluation_trace_is_persisted_and_queryable` 在执行 trace API 前即失败。

开发者本地反馈的实际结果：provider=`ollama`、model=`nomic-embed-text:latest`、dimension=768、cases=5、provider error rate=0、Recall@3=0.6、Precision@3=0.333333、MRR=0.6。该结果与 Phase 2.2-C 已记录的冻结 baseline 一致。

## 根因

代码已将 Real Provider baseline 设计为版本化回归输入，但仓库当前 `main` 缺少与既有冻结质量证据对应的 baseline 文件，导致新加入的 trace Real API test 无法在干净工作树上通过完整 runner gate。

该问题不是通过放宽质量 gate 或自动生成 baseline 解决；baseline 必须来自已实际执行且满足 provider error rate=0 的 Real Provider 结果。

## 影响

- Real Provider Quality Gate 在 baseline 缺失时按设计失败。
- Retrieval evaluation trace 的 Real HTTP API 自动化覆盖无法继续执行。
- Backend Release / Regression Gate 的 Real API 子 gate 被阻塞。

## 修复

将本轮开发者实际反馈且与既有冻结基线一致的 baseline 固化为：

- provider: `ollama`
- model: `nomic-embed-text:latest`
- embedding_dimension: `768`
- dataset_version: `1`
- dataset_sha256: `7bedbe95e2dc122994d42a7c9c29bc0eb7263d895ab5633fc81fc808a0e3cb35`
- retrieval_mode: `real-provider-pgvector`
- top_k: `3`
- Recall@3: `0.6`
- Precision@3: `0.333333`
- MRR: `0.6`

baseline 作为评测资产提交到 `backend/evaluation/knowledge_retrieval_real_baseline.json`。不得通过修改 baseline 掩盖后续质量回归。

## 验证边界

本提交基于开发者提供的 Real Provider runner 实际输出形成 baseline；本次提交后尚未在当前提交上重新执行完整 Backend regression / Real API gate，因此不能在提交时声称这些 Gate 已重新通过。

## 防重复

1. Real Provider runner 在 baseline 缺失时继续保持失败，不自动冻结 baseline。
2. baseline identity 包含 provider、model、dimension、dataset version/hash、retrieval mode、top-k。
3. 后续 Provider、model、dimension、dataset 或 retrieval identity 变化必须触发 regression comparison。
4. 新的 baseline 只能通过显式 `--freeze-baseline` 创建，且 provider error rate 必须为 0。
