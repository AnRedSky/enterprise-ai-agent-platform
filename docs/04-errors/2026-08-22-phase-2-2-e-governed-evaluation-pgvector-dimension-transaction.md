# 2026-08-22 Phase 2.2-E Governed Evaluation pgvector Dimension Transaction Failure

## 问题

使用本地已安装 Ollama 模型执行 governed Embedding Profile smoke 时，Profile A 为 `nomic-embed-text:latest`（768 维），Profile B 使用其他已安装 Embedding 模型时，实际 embedding dimension 与当前 PostgreSQL/pgvector schema dimension 不一致。

当 runner 继续执行 `knowledge_chunks` 写入时，PostgreSQL 事务进入 aborted 状态；随后 fixture cleanup 继续复用同一 `AsyncSession` 执行 DELETE，产生 `InFailedSQLTransactionError`，并进一步触发 Windows Proactor event loop cleanup 异常。最终日志掩盖了最初的 provider/schema dimension 错误。

## 根因

1. Governed Profile 保存的 `dimension` 是实际模型维度。
2. 当前 pgvector 存储 schema 仍以项目配置的 embedding dimension 为契约。
3. Runner 在 Profile dimension 与 vector schema 不一致时没有在进入 fixture 写入前完成明确的 preflight 拒绝。
4. PostgreSQL 写入失败后 cleanup 没有先 rollback，导致原始错误被 `InFailedSQLTransactionError` 覆盖。

## 修复

- `run_knowledge_retrieval_evaluation.py::cleanup_fixture` 在任何 cleanup SQL 前显式 `rollback()`，保证失败事务不会污染清理阶段，并保留原始 provider/schema 错误。
- 后续 governed Profile validation 必须在进入 fixture / vector write 前校验 Profile dimension 与当前 pgvector dimension contract 一致；不允许通过修改 baseline、截断 embedding 或隐式转换维度绕过该约束。

## 本地验证约束

当前本地 Ollama 模型只能使用已经安装的模型，禁止下载新模型。若没有第二个与当前 pgvector dimension 相同的 Embedding 模型，E-2 的“不同 Profile identity 正向 regression”不能宣称通过；应记录为环境能力不足，而不是伪造通过结果。

## 相关测试

```powershell
cd backend
uv run pytest -q tests/unit/test_governed_embedding_profile_smoke.py
uv run pytest -q tests/unit/test_retrieval_evaluation_baseline.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

Governed smoke：

```powershell
cd backend
uv run python .\scripts\evaluation\knowledge\run_governed_embedding_profile_smoke.py `
  --profile-a-model nomic-embed-text:latest `
  --profile-b-model qwen3-embedding:0.6b
```

该命令不得包含 `ollama pull`，也不得下载新模型。
