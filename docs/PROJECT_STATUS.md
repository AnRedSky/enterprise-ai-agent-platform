# Project Status

> 当前项目状态唯一入口。文档治理规则见 `docs/01-governance/DOCUMENTATION.md`，工程开发规则见 `docs/01-governance/DEVELOPMENT.md`。

## 1. 当前基线

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前开发阶段：**Phase 2.2 进行中；2.2-A Contract 已形成，2.2-B 已通过本地 Gate，2.2-C Real Provider Quality Gate 已实现但受当前本地 embedding 模型维度阻塞。**

## 2. Phase 状态

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
| Phase 1.9 | 已完成 / 正式关闭 | Runtime Reliability / Production Hardening |
| Phase 2.1 | 已完成 / 正式关闭 | Enterprise Organization & Access Governance |
| **Phase 2.2** | **进行中** | Retrieval Production Quality；2.2-C 当前受 vector(1536) embedding 模型可用性阻塞 |

## 3. Phase 2.2 当前任务

### 2.2-A — 已形成

Provider / Dataset / Corpus 边界、Recall@K / Precision@K / MRR、Citation correctness、latency、provider error rate、baseline regression 与 failure/fallback semantics 已明确。

### 2.2-B — 本地 Gate 已通过

```text
Dataset Loader: 4 passed
Retrieval evaluation + Dataset: 10 passed
Backend regression: 279 passed, 30 deselected
Migration head: 0023_organization_membership
Real API: 30 passed
2.2-B runner --k 3: 5/5 successful
recall@3=1.0
precision@3=0.466667
MRR=0.9
quality_gate=passed
```

### 2.2-C — 已实现，当前本地环境阻塞

当前 Ollama：

```text
qwen3:0.6b       Chat
nomic-embed-text 768 维
bge-m3           1024 维
```

当前 PostgreSQL/pgvector 契约：

```text
knowledge_chunks -> vector(1536)
```

因此不能直接使用当前两个 embedding 模型执行真实 2.2-C。当前资源约束禁止下载其他模型；禁止截断、补零、隐式改维度或修改指标绕过检查。

Chat `qwen3:0.6b` 可以用于 Runtime / UI 本地调试，但不能替代 Embedding Provider，也不能作为 Retrieval Quality baseline。

### 本轮实际验证

```text
Ollama /api/tags: 3 models available
Model Gateway unit: 5 passed
Backend regression: 287 passed, 30 deselected
Migration head: 0023_organization_membership
Real API: 30 passed
```

手工 PowerShell `/v1/chat/completions` 曾因 JSON quoting 返回：

```text
invalid character 'm' looking for beginning of object key string
```

已新增 `backend/scripts/dev/ollama_chat_smoke.ps1`，使用 `ConvertTo-Json` + `Invoke-RestMethod` 规避 shell quoting 差异；该工程错误已记录到 `docs/04-errors/`。

Frontend 测试命令曾使用缺少 `.ps1` 扩展名的 `-File` 路径；正确命令必须是：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

### 下一步

1. 执行 `backend/scripts/dev/ollama_chat_smoke.ps1` 验证 Chat Provider。
2. 保持 Backend / Frontend / Browser Gate 独立。
3. 不下载其他模型，不伪造 embedding baseline。
4. 获得可实际产生 1536 维 embedding 的已部署 Provider，或明确批准调整 pgvector 维度后，执行 2.2-C `--freeze-baseline`。
5. 真实 2.2-C baseline 冻结后进入 2.2-D Retrieval Quality Regression。

## 4. 文档维护

功能完成、延期、阻塞、范围变化或已分析工程错误均同步更新 `PROJECT_STATUS.md`、对应 Phase / Acceptance 文档及 `docs/04-errors/`。同一任务产生的多份文档变更应作为一个原子文档变更集提交。
