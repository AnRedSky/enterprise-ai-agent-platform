# Project Status

> 当前项目状态唯一入口。文档治理规则见 `docs/01-governance/DOCUMENTATION.md`，工程开发规则见 `docs/01-governance/DEVELOPMENT.md`。

## 1. 当前基线

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 最新产品基线：Phase 2.1 Enterprise Organization & Access Governance 已完成最终联合验收并正式关闭。
- 开发原则：所有任务直接基于最新 `main`；禁止创建功能分支、临时分支或长期分支。
- 当前开发阶段：**Phase 1.9 已完成 / 正式关闭；Phase 2.1 已完成 / 正式关闭；Phase 2.2 进行中，2.2-A Contract 已形成，2.2-B 已通过本地 Gate，2.2-C Real Provider Quality Gate 已实现但受当前本地 embedding 模型维度阻塞。**
- 产品能力基线：`docs/PRODUCT_CAPABILITY_BASELINE.md`
- 产品与功能开发对比矩阵：`docs/PRODUCT_DEVELOPMENT_MATRIX.md`
- 产品整体路线：`docs/PRODUCT_ROADMAP.md`

## 2. Phase 2.1 最终联合验收证据

历史最终联合验收证据保持不变：Frontend 16 files / 69 tests + build、Backend 275 passed、Real API 30 passed、Organization Browser E2E 3 passed。

**Phase 2.1 正式关闭。**

## 3. Phase 状态

| Phase | 状态 | 说明 |
|---|---|---|
| Phase 1.0 | 已完成 | 基础项目初始化与最小能力 |
| Phase 1.2 | 已完成 | 基础平台、Auth/RBAC、Agent、Session、Runtime、Model/Tool 基础能力 |
| Phase 1.3 | 已完成当前历史范围 | Model Gateway / Tool Runtime / Memory / Observability |
| Phase 1.4 | 已完成当前历史范围 | Knowledge / RAG / Retrieval；真实 Provider 语义质量保持验证边界 |
| Phase 1.5 | 已完成 / 正式关闭 | Workflow / Governance / Reliability / Circuit Breaker 基础能力 |
| Phase 1.6 | 已完成 / 正式关闭 | Trigger / Frontend / Browser 历史范围 |
| Phase 1.7 | 已完成 / 正式关闭 | Scheduled Trigger / Governance / Browser E2E |
| Phase 1.8 | 已完成 / 正式关闭 | Event / Webhook Trigger Expansion |
| Phase 1.9 | 已完成 / 正式关闭 | Runtime Reliability / Production Hardening 全部 Acceptance Gate 通过 |
| **Phase 2.1** | **已完成 / 正式关闭** | Enterprise Organization & Access Governance；A～F-C 全部 Gate 与最终联合验收通过 |
| **Phase 2.2** | **进行中** | Retrieval Production Quality；2.2-A 已形成，2.2-B 本地 Gate 已通过，2.2-C runner 已实现但当前本地 embedding 模型无法满足 vector(1536) 契约 |
| Phase 2.3～2.8 | 路线候选 | Model Governance、Durable Scheduler、Advanced Workflow、Event Infrastructure、Multi-Agent、Agent Marketplace |

## 4. Phase 2.2 当前任务

### 2.2-A Product / Retrieval Quality Contract — **已形成**

已明确 Provider / Dataset / Corpus 边界、Recall@K / Precision@K / MRR、Citation correctness、latency、provider error rate、baseline regression 与 failure/fallback semantics。真实 Provider Quality Gate 尚未通过。

### 2.2-B Evaluation Dataset / Runner — **本地 Gate 已通过**

本地实际证据：

```text
Dataset Loader: 4 passed
Retrieval evaluation + Dataset: 10 passed
Backend regression: 279 passed, 30 deselected
Migration head: 0023_organization_membership
Real API: 30 passed
2.2-B runner --k 3: 5/5 cases successful, error_rate=0, recall@3=1.0, precision@3=0.466667, MRR=0.9, quality_gate=passed
```

### 2.2-C Real Provider Quality Gate — **实现完成，当前本地环境阻塞**

Runner 已实现真实 Provider、真实 PostgreSQL/pgvector、baseline freeze、identity comparison、provider failure / fallback evidence。

当前开发者本地 Ollama 已确认：

```text
qwen3:0.6b              Chat
nomic-embed-text        768 维 embedding
bge-m3                  1024 维 embedding
```

数据库当前契约：

```text
knowledge_chunks -> vector(1536)
```

因此现有 embedding 模型不能直接执行 2.2-C Real Provider Quality Gate。当前资源约束禁止下载其他模型，所以不能通过增加模型解决问题，也不能截断、补零或修改指标绕过维度检查。

当前处理方式：

- `.env.example` 保持 Retrieval Embedding Mock，保证开发/测试零配置。
- Chat 使用 Ollama `qwen3:0.6b`，不可用时允许 Chat Mock fallback。
- 2.2-C 不冻结虚假 baseline。
- 待出现实际可产生 1536 维 embedding 的已部署 Provider，或项目明确批准修改 pgvector 维度后，再执行 Real Provider Quality Gate。

### 本轮本地验证

开发者实际反馈：

```text
Ollama /api/tags: 3 models available
Model Gateway unit: 5 passed
Backend regression: 287 passed, 30 deselected
Migration head: 0023_organization_membership
Real API: 30 passed
```

PowerShell 手工 `/v1/chat/completions` 曾因 JSON quoting 返回：

```text
invalid character 'm' looking for beginning of object key string
```

已新增 `backend/scripts/dev/ollama_chat_smoke.ps1`，使用 `ConvertTo-Json` + `Invoke-RestMethod`，避免 shell quoting 差异。该问题已记录到 `docs/04-errors/`，不认定为 Ollama 服务故障。

Frontend 命令反馈中的：

```text
-File .\scripts\test\release\01_frontend_regression_gate.
```

缺少 `.ps1` 扩展名，属于命令输入错误。正确入口见 `docs/01-governance/DEVELOPMENT.md`。

### 下一步

1. 使用新增 Ollama smoke test 确认 `qwen3:0.6b` Chat endpoint。
2. 继续保持 Backend / Frontend Gate 独立。
3. 不下载其他模型、不伪造 embedding baseline。
4. 在真实 1536 维 embedding Provider 可用后执行 2.2-C `--freeze-baseline`，再进入 2.2-D Retrieval Quality Regression。
5. 2.2-D 可以准备比较/报告基础设施，但最终 regression Gate 必须依赖真实 2.2-C baseline。

## 5. 维护规则

后续任何功能完成、延期、阻塞、范围变化或新的工程错误，都必须同步：

- `docs/PROJECT_STATUS.md`
- 对应 `docs/02-phases/PHASE_x_y.md`
- 对应 `docs/03-acceptance/PHASE_x_y_ACCEPTANCE.md`
- 已分析完成的工程错误同步 `docs/04-errors/`

同一任务的多份文档变更应作为一个文档变更集一次性提交，避免每个文档形成独立中间提交。
