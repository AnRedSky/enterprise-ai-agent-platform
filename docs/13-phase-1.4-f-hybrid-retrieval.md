# Phase 1.4-F：Hybrid Retrieval Contract

> 本阶段继续遵循 `docs/DEVELOPMENT.md`：直接提交 `main`，本地执行测试，不执行 GitHub Actions CI。

## 1. 目标

在已经稳定的 `lexical-v2` 与 `vector` retrieval contract 之上，建立 provider-neutral Hybrid Retrieval 边界：

```text
Query
 ├─ lexical-v2 ──┐
 │               ├─ score fusion ──> hybrid ranking
 └─ vector ──────┘
```

第一版不引入新的向量数据库、不把 pgvector SQL 暴露到业务层，也不引入模型型 reranker。

## 2. F-01 实现范围

新增 `HybridRetrievalService` 与以下 contract：

- `HybridCandidate`：统一描述 chunk、0..1 score、来源及业务 payload。
- `HybridRetrievalConfig`：控制 lexical / vector 权重。
- `HybridRetrievalService.fuse()`：对两个 provider-neutral candidate 集合执行确定性加权融合。
- 同一 chunk 在单一来源重复出现时取最高 score。
- 仅命中 lexical 或 vector 的 chunk 仍可进入候选集合，缺失来源按 0 分处理。
- 最终 score 仍保持 0..1。
- score 相同时按 `chunk_id` 稳定排序，避免依赖数据库返回顺序。

当前默认权重：

```text
lexical_weight = 0.5
vector_weight  = 0.5
```

实际融合公式：

```text
fused_score =
  (lexical_weight * lexical_score + vector_weight * vector_score)
  / (lexical_weight + vector_weight)
```

## 3. 边界

本次只完成 **Hybrid Retrieval Contract / score fusion**，暂不把它直接接入 Retrieval API。

后续 F-02 才负责：

1. lexical-v2 / vector 两路真实检索调用编排；
2. Knowledge Base / Document RBAC 保持在两路检索内部；
3. candidate hydration / citation 保持现有 contract；
4. `mode=hybrid` API contract；
5. Recall@K / Precision@K / MRR 评测与权重调优。

## 4. 测试

新增：

```text
backend/tests/test_hybrid_knowledge_retrieval.py
```

覆盖：

- weighted fusion；
- 双路候选合并；
- 单路候选；
- 同来源重复 chunk 取最高分；
- 权重校验；
- score / top-k 参数校验；
- stable tie-breaking。

### 本地验证命令

```powershell
cd backend
uv run pytest -q tests/test_hybrid_knowledge_retrieval.py
uv run pytest -q
```

代码提交前的实际测试结果必须以开发者本地执行反馈为准；当前文档不预填未执行的结果。

## 5. 当前状态

- 1.4-E mock Embedding + PostgreSQL/pgvector deterministic retrieval：**本地验收通过**。
- 本地反馈指标：Recall@3=1.0、Precision@3=0.466667、MRR=0.9、error_rate=0、quality gate=passed。
- 真实 Embedding provider semantic quality：**尚未验证**，原因是当前环境没有真实 Embedding Provider。
- 1.4-F-01 Hybrid Retrieval contract：**已实现，待本地 pytest 验证**。

## 6. 下一阶段任务

| ID | 任务 | 优先级 | 状态 | 责任角色 | 前置依赖 | 目标时间 |
|---|---|---|---|---|---|---|
| 1.4-F-02 | 将 lexical-v2 + vector 接入 Hybrid Retrieval Service，并增加 `mode=hybrid` API | P1 | 待本地验证 F-01 后开始 | Backend / Knowledge | F-01、本地 pytest | 2026-08-20 |
| 1.4-F-03 | 使用固定 Evaluation Dataset 做 hybrid 权重评测与 quality gate | P1 | 未开始 | Backend / QA | F-02 | 2026-08-21 |
| 1.4-G-01 | Retrieval Debug 增加 hybrid 来源/分数拆解展示 | P1 | 未开始 | Frontend | F-02 | 2026-08-22 |
| 1.4-G-02 | Runtime execution / trace 与 Retrieval Debug 关联 | P1 | 未开始 | Backend / Frontend | G-01 | 2026-08-24 |

真实 Embedding Provider、外部 endpoint、API key 和数据库凭据仍只允许存在本地未提交 `backend/.env`。
