# Project Status

> 当前项目状态唯一入口。文档治理规则见 `docs/01-governance/DOCUMENTATION.md`，工程开发规则见 `docs/01-governance/DEVELOPMENT.md`。

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：进行中。
- 2.2-A Contract：已形成。
- 2.2-B Dataset / Runner：已通过本地 Gate。
- 2.2-C Real Provider Quality Gate：已实现，当前受本地 embedding 模型维度阻塞。

## 2.2-B 实际证据

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

## 2.2-C 当前边界

当前 Ollama 模型：

```text
qwen3:0.6b       Chat
nomic-embed-text 768 维 embedding
bge-m3           1024 维 embedding
```

当前 pgvector 契约为 `vector(1536)`，所以现有 embedding 模型不能直接用于真实 2.2-C。当前资源约束禁止下载其他模型；禁止截断、补零、隐式改维度或修改指标绕过检查。

`qwen3:0.6b` 可以用于 Runtime / UI Chat 调试，但不能替代 Embedding Provider 或 Retrieval Quality baseline。

## 本轮本地验证

```text
Ollama /api/tags: 3 models available
Model Gateway unit: 5 passed
Backend regression: 287 passed, 30 deselected
Migration head: 0023_organization_membership
Real API: 30 passed
```

PowerShell 手工 Chat 请求曾因 JSON quoting 返回 `invalid character 'm' looking for beginning of object key string`。已新增 `backend/scripts/dev/ollama_chat_smoke.ps1`，使用 `ConvertTo-Json` + `Invoke-RestMethod`，并记录工程错误到 `docs/04-errors/`。

Frontend Gate 正确入口：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

## 下一步

1. 执行 Ollama Chat smoke test。
2. 保持 Backend / Frontend / Browser Gate 独立。
3. 不下载其他模型，不伪造 embedding baseline。
4. 获得可实际产生 1536 维 embedding 的已部署 Provider，或明确批准调整 pgvector 维度后，执行 2.2-C `--freeze-baseline`。
5. 真实 2.2-C baseline 冻结后进入 2.2-D Retrieval Quality Regression。

## 文档维护

功能完成、延期、阻塞、范围变化或已分析工程错误必须同步项目状态、Phase / Acceptance 文档及 `docs/04-errors/`。同一任务的多份文档变更应作为一个原子文档变更集提交。
