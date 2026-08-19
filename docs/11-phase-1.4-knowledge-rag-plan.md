# Phase 1.4：Knowledge / RAG 功能闭环规划与执行基线

> 本文是 Phase 1.4 的开发基线。所有开发直接提交 `main`，不创建新的功能分支。固定开发顺序以 `docs/DEVELOPMENT.md` 为准。

## 1. 阶段目标

Phase 1.4 聚焦 Knowledge / RAG，目标不是一次性接入某个具体向量数据库，而是先建立与现有 Agent Runtime、RBAC、Observability 解耦的知识领域边界，并形成可验收闭环：

```text
Knowledge Base → Document → Version → Chunk → Index / Retrieval contract → Context Builder → Agent Runtime → Citation / Trace
```

## 2. 后端并行开发顺序

### 1.4-A Knowledge Registry
- [x] KnowledgeBase 元数据、Owner、状态
- [x] Document 元数据、来源、状态、版本关联
- [x] RBAC owner isolation
- [x] CRUD API 与分页
- [x] Alembic migration `0007_knowledge_registry`
- [x] Backend pytest：API contract 回归测试已提交
- [x] 独立手工验收脚本：`backend/scripts/run_knowledge_registry_scenario.ps1`
- [x] 本地手工验收：Knowledge Registry 场景已通过（CRUD、Version、分页、删除、Owner/RBAC）

### 1.4-B Document ingestion
- [x] 文档内容抽象与 parser/cleaner contract
- [x] 清洗、确定性分块策略 contract
- [x] Chunk 持久化：migration `0008_knowledge_ingestion`
- [x] 增量重新摄取：同一 Version 先删除旧 Chunk 再生成新 Chunk
- [x] ingestion 状态机：`pending → processing → ready / failed`
- [x] Chunk 与 Document Version 可追溯
- [x] Backend pytest：chunk contract / API contract
- [x] 独立手工验收脚本：`backend/scripts/run_knowledge_ingestion_scenario.ps1`
- [x] 本地手工验收：Version → Ingest → Chunks → Re-ingest 已通过

### 1.4-C Retrieval contract
- [x] Embedding provider interface
- [x] Retriever interface
- [x] Reranker interface（先定义 contract）
- [x] Provider-neutral retrieval result
- [x] source document / chunk / relevance score / citation
- [x] 第一版 provider-neutral lexical retrieval 实现，不绑定具体向量数据库
- [x] Knowledge Base owner isolation 在检索查询阶段执行
- [x] 独立手工验收脚本：`backend/scripts/run_knowledge_retrieval_scenario.ps1`
- [x] 本地 pytest + Retrieval 手工验收已通过

### 1.4-D Runtime integration
- [x] AgentVersion 可声明 Knowledge 配置（`knowledge_base_ids` + `top_k`）
- [x] Runtime Context Assembly 接入检索结果
- [x] 保持 `execution_id / trace_id / agent_version` 链路
- [x] 权限过滤必须发生在检索结果进入模型上下文之前
- [x] 引用结果通过 SSE start/done 事件向调用方返回
- [x] Retrieval span 写入 Observability
- [x] Runtime + Knowledge 联调手工验收
- [x] 前后端第一轮回归

### 1.4-E Knowledge / Retrieval 生产化深化
- [x] 检索策略升级为 deterministic `lexical-v2`，保持 provider-neutral
- [x] 中文短语增加序列/二元 token，避免连续中文文本无法命中
- [x] `min_score` 阈值控制，避免低相关候选进入上下文
- [x] 可选重复 Chunk 去重，降低重复上下文
- [x] 返回 `matched_terms` 与 `retrieval_mode`，支持 Retrieval Debug 质量分析
- [x] 候选扫描设置上限并保持稳定排序，避免结果顺序随数据库返回顺序漂移
- [x] Retrieval API schema 与前端 API 类型同步升级
- [x] 增加 retrieval quality / API contract 单元测试
- [x] 增加离线 Evaluation Case contract：Recall@K / Precision@K / MRR
- [x] 增加基线 Retrieval Evaluation Dataset：`backend/evaluation/knowledge_retrieval_dataset.jsonl`
- [x] 增加 provider-neutral 离线评测 runner：`backend/scripts/evaluate_knowledge_retrieval.py`
- [ ] 用真实 lexical retrieval 输出运行 Evaluation Dataset，形成基线指标快照
- [ ] 与真实 Embedding / Vector DB provider 的替换性联调
- [ ] 真实 provider 上的 Recall / Precision / MRR 对比评测

## 3. 前端并行开发顺序

### 1.4-F Knowledge 管理端
- [x] 独立 `src/views/knowledge/index.vue + components/KnowledgeWorkbench.vue`
- [x] Knowledge Base 列表 / 创建 / 状态展示
- [x] Document 列表 / 创建 / 删除
- [x] Document Version 展示 / 创建
- [x] Chunk 查看
- [x] ingestion 状态与 Ingest 操作
- [x] 错误、空状态基础处理
- [x] 独立 `tests/views/knowledge/KnowledgeWorkbench.test.ts`

### 1.4-G Retrieval / Debug
- [x] Retrieval 调试入口
- [x] query / top-k / Knowledge Base 过滤
- [x] source document / score / citation / content 展示
- [x] 与 Retrieval API 的 `retrieval_mode / matched_terms / min_score` contract 对齐
- [ ] 与 Runtime execution 关联

前端只通过 `/api/v1` 调用后端，不实现 Knowledge 核心业务规则。

## 4. 联调顺序

每个小版本必须按以下顺序推进：

1. Backend contract + migration + pytest
2. Frontend API types + Vitest
3. Frontend UI
4. API scenario / 手工验收脚本
5. Runtime integration
6. 前后端联调
7. `backend pytest` + `frontend npm test` + `frontend npm run build`
8. 更新验收文档后提交 `main`

禁止先做孤立 UI，再反向修改 API；禁止前后端各自定义不同的领域模型。

## 5. 第一轮验收标准

- Knowledge Base owner 隔离有效
- Document CRUD / version 可追踪
- ingestion 状态可查询
- Chunk 可追溯到 Document Version
- Retrieval contract 返回标准 source / score / citation
- 未授权用户无法读取其他 Owner 的知识内容
- Runtime 接入前不允许把未授权 chunk 放入 prompt
- 所有知识检索执行能够关联 execution / trace
- 前后端测试脚本保持独立

## 6. 当前状态

**Phase 1.4-A / B / C / D 已完成本地验收；Phase 1.4-E 已进入 Retrieval Evaluation 与 provider replacement validation。** 当前 lexical-v2 retrieval 已具备 deterministic ranking、中文短语 tokenization、min_score、dedupe、candidate cap 和 retrieval metadata。此次继续补齐了离线评测指标 contract、5 条基线 Evaluation Dataset 与 provider-neutral runner。下一步先用真实 lexical retrieval 输出跑出基线 Recall@K / Precision@K / MRR，再进行真实 Embedding / Vector DB provider 替换性验证。

## 7. 暂不在第一轮实现

- 强绑定 Milvus / Elasticsearch 等具体基础设施
- 自动 OCR 全套能力
- 复杂 reranker 模型部署
- Knowledge 多租户高级策略
- 生产级异步 MQ / 分布式 ingestion

这些能力在第一轮 contract 闭环完成后再逐步实现，避免架构过早绑定。
