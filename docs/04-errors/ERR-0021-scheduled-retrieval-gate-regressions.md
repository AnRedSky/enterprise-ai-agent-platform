# ERR-0021 — Scheduled Trigger 与 Real Retrieval Gate 回归失败

- 日期：2026-08-22
- 范围：Phase 2.2 / Backend Real API / Real Provider Quality Gate
- 触发提交：`cdbfae1 fix(retrieval): preserve real baseline identity for runtime bridge`

## 问题现象

开发者在最新 `main` 上执行 Backend Release / Regression Gate 时出现两个 Scheduled Trigger Real HTTP 失败：

1. Scheduler 已创建 durable `workflow_executions` 行，但测试在 execution 仍为 `pending` 时立即断言 `completed`。
2. 双 worker 测试使用默认 `recovery_slots=2`，一次 `tick_once()` 同时处理当前 slot 与 recovery slot，因此两个 worker 的 `dispatched` 总数可能为 2；测试实际只意图验证同一个 slot 的竞争收敛。

同一轮真实 Retrieval Provider runner 还出现全部 5 个 case 的 retrieval ranking 为空，Recall@3 / MRR 从 baseline 0.6 回归到 0.0，provider error rate 为 0。

## 根因

### Scheduled Trigger

Real API 测试的轮询辅助函数只要发现 execution 行就立即返回，没有等待 terminal state。Scheduler 的 durable claim 与 Runtime execution 是两个连续阶段，因此 `pending` 是合法的短暂中间状态。

双 worker 测试没有隔离 recovery window。`tick_once()` 的职责是处理 bounded recovery slots；默认窗口包含当前 slot 和历史 recovery slot，所以该测试的 `dispatched` 计数并不只代表目标 current slot。

### Real Retrieval

`run_knowledge_retrieval_evaluation.py` 的共享 evaluation fixture 将 `knowledge_document_versions.status` 写为 `published`、`ingestion_status` 写为 `completed`，而 `VectorKnowledgeRetrievalService` 的正式 hydration contract 要求：

- `KnowledgeDocument.status = active`
- `KnowledgeDocumentVersion.status = ready`
- `KnowledgeDocumentVersion.ingestion_status = ready`
- `KnowledgeDocumentVersion.vector_index_status = ready`

因此底层 pgvector 已有向量，但正式 Runtime Retrieval 在 hydration 阶段全部过滤掉，最终 ranking 被转换为空。

## 修复

1. Real API scheduled execution polling 改为等待 execution 进入 terminal state，再执行 `completed` contract 断言。
2. 双 worker convergence test 显式使用 `recovery_slots=1`，只验证同一 current slot 的 durable idempotency claim。
3. Evaluation fixture 使用与生产 Retrieval Service 一致的 `ready / ready / processing -> ready` 生命周期：fixture 写入后再由 runner 将 `vector_index_status` 更新为 `ready`。

## 预防

- Real API 测试必须区分 durable record creation 与 Runtime terminal completion。
- 验证单一 scheduler slot 的竞争时，必须显式收窄 recovery window。
- Evaluation fixture 的状态枚举必须复用业务 Retrieval 的实际 hydration contract，不得只满足底层 repository 查询。
- Real Provider Gate 失败时不得重写 baseline；必须保留 regression evidence。

## 验证边界

本次远程代码操作环境没有开发者本地 PostgreSQL、Ollama、API 进程和完整 Windows 工作区，因此本修复提交前未实际执行 `uv run pytest`、Alembic 或 Real API Gate。开发者必须在本地重新执行固定 Gate，并以实际结果更新项目状态；不得将本文件的修复描述视为测试通过证据。
