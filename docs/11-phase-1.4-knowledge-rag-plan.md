# Phase 1.4：Knowledge / RAG 功能闭环规划与执行基线

> 本文是 Phase 1.4 的开发基线。所有开发直接提交 `main`，不创建新的功能分支。

## 1. 阶段目标

Phase 1.4 聚焦 Knowledge / RAG，目标不是一次性接入某个具体向量数据库，而是先建立与现有 Agent Runtime、RBAC、Observability 解耦的知识领域边界，并形成可验收闭环：

```text
Knowledge Base
  → Document
  → Version
  → Chunk
  → Index / Retrieval contract
  → Context Builder
  → Agent Runtime
  → Citation / Trace
```

## 2. 后端并行开发顺序

### 1.4-A Knowledge Registry

- KnowledgeBase 元数据、Owner、状态、版本
- Document 元数据、来源、状态、版本
- RBAC owner isolation
- CRUD API 与分页
- Alembic migration
- pytest 回归测试

### 1.4-B Document ingestion

- 文档内容抽象与 parser contract
- 清洗、分块策略 contract
- Chunk 持久化
- 增量更新与删除状态
- ingestion 状态机：`pending → processing → ready / failed`

### 1.4-C Retrieval contract

- Embedding provider interface
- Retriever interface
- Reranker interface（先定义 contract）
- Provider-neutral retrieval result
- source document / chunk / relevance score / citation

### 1.4-D Runtime integration

- AgentVersion 可声明 Knowledge 配置
- Runtime Context Assembly 接入检索结果
- 保持 `execution_id / trace_id / agent_version` 链路
- 权限过滤必须发生在检索结果进入模型上下文之前
- 引用结果写入 Observability

## 3. 前端并行开发顺序

### 1.4-F Knowledge 管理端

- Knowledge Base 列表 / 创建 / 状态
- Document 列表 / 上传入口 / ingestion 状态
- Document Version 展示
- 错误、空状态、分页

### 1.4-G Retrieval / Debug

- 检索调试入口
- query、top-k、过滤条件
- source chunk / score / citation 展示
- 与 Runtime execution 关联

前端只通过 `/api/v1` 调用后端，不实现 Knowledge 核心业务规则。

## 4. 联调顺序

每个小版本必须按以下顺序推进：

1. Backend contract + migration + pytest
2. Frontend API types + Vitest
3. API scenario / 手工验收脚本
4. Runtime integration
5. 前后端联调
6. `backend pytest` + `frontend npm test` + `frontend npm run build`
7. 更新验收文档后提交 `main`

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

## 6. 暂不在第一轮实现

- 强绑定 Milvus / Elasticsearch 等具体基础设施
- 自动 OCR 全套能力
- 复杂 reranker 模型部署
- Knowledge 多租户高级策略
- 生产级异步 MQ / 分布式 ingestion

这些能力在第一轮 contract 闭环完成后再逐步实现，避免架构过早绑定。
