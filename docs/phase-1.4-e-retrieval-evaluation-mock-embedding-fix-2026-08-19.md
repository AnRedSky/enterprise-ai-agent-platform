# Phase 1.4-E Retrieval Evaluation：Mock Embedding 中文检索修复记录

日期：2026-08-19  
任务：1.4-E-04 / Retrieval Evaluation 离线质量验证  
责任角色：Backend / Knowledge  
状态：**代码修复已提交，待本地重新执行完整 Quality Gate 验证**

## 1. 问题现象

本地执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase_1_4_e_provider_validation.ps1
```

前 3 个阶段通过：

- Embedding provider contract：3 passed
- pgvector contract：7 passed
- Backend regression：139 passed
- pgvector round-trip：dimension=1536、top_k=5、score=1.0

第 4 阶段生成了 5 条 `evaluation/vector_results.jsonl`，但 Quality Gate 失败：

```text
recall_at_k = 0.6
precision_at_k = 0.266667
mrr = 0.5
avg_latency_ms = 2.426
error_rate = 0.0
```

失败原因：Recall@K 和 MRR 均低于 lexical-v2 baseline 的 1.0。

## 2. 根因分析

当前 Phase 1.4-E 离线验证使用的是 `MockEmbeddingProvider + PostgreSQL/pgvector`。该 provider 的定位是**确定性离线管线验证**，并不代表真实 Embedding 模型的语义质量。

原实现将连续中文文本作为一个整体 token。例如：

```text
查询：报销规则
文档：报销规则规定员工报销的申请条件……
```

查询 token 与文档中的完整连续中文 token 不一致，因此共享特征不足；同样问题会影响“审批流程”等中文短查询。这会使离线 mock vector 排名不能稳定覆盖固定 Evaluation Dataset。

该问题属于 mock provider 的测试数据特征构造缺陷，不属于 pgvector、Vector Retrieval SQL 或真实 Provider 的语义质量结论。

## 3. 实现修复

修改：

- `backend/app/services/mock_embedding_provider.py`
- `backend/tests/test_mock_embedding_provider.py`

新的确定性特征策略：

1. 英文单词/标识符继续作为完整 token。
2. 中文连续文本保留整体 token。
3. 中文连续文本额外生成重叠二元字符特征。
4. Query 与较长中文 Chunk 因共享中文 bigram 获得稳定相似度。
5. 仍保持固定 hash → vector dimension 的确定性方式。
6. 明确保持 mock provider 不能证明真实模型语义质量的边界。

新增回归测试覆盖：

```text
报销规则
→ 报销规则规定员工报销的申请条件、金额限制、票据要求以及审批流程。
```

## 4. 代码提交

修复提交：

- `e94aeb790146639e3c0be1eba53fbf18dff277c8`：Mock Embedding 中文特征修复
- `38e6cd2634037fcfc52eb4a3b335f7ebb47bc1bf`：中文检索回归测试

按照项目开发准则，变更直接提交 `main`，未创建功能分支。

## 5. 测试结果

### 已由开发侧确认

本次修改基于失败样本完成根因定位和代码修复；GitHub 代码已提交。

### 待本地执行并记录

必须由本地开发环境重新执行以下命令后，才能将 Quality Gate 标记为通过：

```powershell
uv run pytest tests/test_mock_embedding_provider.py -q
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase_1_4_e_provider_validation.ps1
```

不得在本文件中预先宣称真实 Provider 或 Quality Gate 已通过。

## 6. 已知问题与边界

1. Mock Embedding 只用于离线、确定性 pipeline 验证。
2. Mock Embedding 的 Recall/Precision/MRR 通过不代表真实 Embedding 模型语义质量通过。
3. 真实 Embedding Provider 仍需要使用相同 Dataset、Knowledge Base scope、top-k 和相关性标注进行独立验证。
4. 当前项目仍处于 Phase 1.4-E，不能因 mock-pgvector Quality Gate 通过而提前进入 1.4-F Hybrid Retrieval 验收。

## 7. 下一阶段任务

| ID | 任务 | 优先级 | 前置依赖 | 责任角色 | 目标时间 |
|---|---|---|---|---|---|
| 1.4-E-04 | 重新执行 mock-pgvector Retrieval Evaluation，确认中文特征修复后的 Recall/MRR | P0 | 本次代码修复 | Backend / QA | 2026-08-19 |
| 1.4-E-01 | 使用真实 Embedding Provider 完成固定 Dataset 端到端向量入库与检索 | P0 | 本地 Provider endpoint/API key | Backend / Knowledge | 2026-08-20 |
| 1.4-E-02 | 采集真实 vector `vector_results.jsonl` 并执行 Quality Gate | P0 | 1.4-E-01 | Backend / QA | 2026-08-20 |
| 1.4-E-03 | 对比 lexical-v2 与真实 vector 的 Recall/Precision/MRR/latency/error rate | P0 | 1.4-E-02 | Knowledge / QA | 2026-08-20 |
| 1.4-E-05 | 更新 Provider Replacement Validation 验收结论 | P0 | 1.4-E-03/04 | Tech Lead | 2026-08-21 |
| 1.4-F-01 | Hybrid Retrieval 设计与 Contract | P1 | 1.4-E 验收通过 | Architecture / Backend | 2026-08-24 |

## 8. 验收结论

当前结论：**1.4-E 未完成验收**。

本次失败已定位为 mock embedding 中文特征构造问题并完成代码修复，但必须等待本地重新执行测试和 Quality Gate 后，才能更新为“通过”。真实 Embedding Provider 的质量结论仍保持待验收状态。
