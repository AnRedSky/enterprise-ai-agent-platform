# Phase 1.4-E Retrieval Evaluation Runner 修复记录（2026-08-19）

## 1. 任务状态

- 任务：修复 `scripts/run_knowledge_retrieval_evaluation.py` 在真实 PostgreSQL/pgvector 环境执行时的 fixture 初始化失败。
- 优先级：P0
- 责任角色：Backend / Knowledge
- 当前状态：代码修复已提交 `main`，**待本地重新执行验证**。
- 关联提交：`a504a81a136c3ea24e76212be7230240d06dfc18`

## 2. 问题与根因

本地执行：

```powershell
uv run python scripts/run_knowledge_retrieval_evaluation.py --k 3
```

失败位置为 `prepare_fixture()` 创建 `knowledge_bases` 记录时：

```text
NotNullViolationError: null value in column "created_at" of relation "knowledge_bases"
```

根因是该 evaluation runner 使用 SQLAlchemy `text()` 执行原生 SQL INSERT。SQLAlchemy ORM 模型中的 `default=datetime.utcnow` 只在 ORM 对象构造/flush 路径生效，不能保证原生 SQL INSERT 自动填充数据库字段，因此 fixture 初始化必须显式提供非空时间字段。

## 3. 实现细节

已修改：

- `backend/scripts/run_knowledge_retrieval_evaluation.py`
- `knowledge_bases` INSERT 显式写入 `created_at`、`updated_at`。
- `knowledge_documents` INSERT 显式写入 `created_at`、`updated_at`。
- `knowledge_document_versions` INSERT 显式写入 `created_at`。
- `knowledge_document_chunks` INSERT 显式写入 `created_at`。
- 使用 PostgreSQL `CURRENT_TIMESTAMP`，保持 fixture 与数据库服务器时间一致。
- 未修改业务表结构、Alembic migration 或生产数据模型；本次变更仅修复评测脚本的 ephemeral fixture 初始化。

## 4. 已知问题与解决方案

### 已知问题

首次运行在 fixture 创建阶段失败，因此没有生成：

```text
evaluation/vector_results.jsonl
```

随后直接执行结果评估脚本会因输入文件不存在而失败，这是前序 runner 失败导致的连锁结果，并非 evaluator 本身的质量门禁错误。

### 解决方案

先修复 fixture 初始化，再按固定顺序执行：

1. Retrieval evaluation runner 生成 `evaluation/vector_results.jsonl`。
2. 使用 evaluator 对生成的 JSONL 执行 Recall@K / Precision@K / MRR / latency / error rate 评估。
3. 由统一 Phase 1.4-E provider validation 脚本执行完整质量门禁。

## 5. 测试记录

### 本次反馈中已确认

- PostgreSQL + pgvector round-trip probe：通过。
- `uv run pytest -q`：`139 passed, 86 warnings`。
- `uv run python scripts/validate_pgvector.py`：通过，`dimension=1536, top_k=5, score=1.0`。

### 本次修复后

尚未由开发环境重新执行 `run_knowledge_retrieval_evaluation.py --k 3`，因此本记录**不将 runner 或 Quality Gate 标记为通过**。

## 6. 下一阶段任务清单

| 任务 | 优先级 | 前置依赖 | 目标时间 | 状态 |
|---|---|---|---|---|
| 重新执行 retrieval evaluation runner，确认 fixture 初始化与 pgvector 检索均成功 | P0 | 本次修复 | 2026-08-19 | 待本地验证 |
| 检查 `evaluation/vector_results.jsonl` 是否生成，并运行 evaluator | P0 | runner 通过 | 2026-08-19 | 待开始 |
| 执行 Phase 1.4-E 完整 provider validation | P0 | evaluator 通过 | 2026-08-19 | 待开始 |
| 使用真实 Embedding Provider 完成同 Dataset 的端到端质量验证 | P0 | 本地真实 Provider 配置 | 2026-08-20 | 待资源 |
| 完成 lexical-v2 与 vector quality 对比并形成验收结论 | P0 | vector results | 2026-08-20 | 待开始 |
| 进入 Hybrid Retrieval 设计与 Contract | P1 | 1.4-E 验收通过 | 2026-08-24 | 未开始 |

## 7. 资源协调

- PostgreSQL/pgvector：本地已有可用验证环境，前序 round-trip 已通过。
- Embedding：当前 evaluation runner 使用 deterministic Mock Embedding；该路径只验证 embedding contract + pgvector 检索链路，不代表真实模型语义质量。
- 真实 Embedding Provider：仍依赖开发者本地 `.env` 配置 endpoint / API key / model；密钥不得提交 Git。
- CI：根据 `docs/DEVELOPMENT.md`，当前阶段不执行或触发 GitHub Actions CI。
