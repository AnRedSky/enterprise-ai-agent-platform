# Knowledge / Runtime 集成检查清单

## Backend

- [ ] `uv sync` 成功
- [ ] `uv run alembic upgrade head` 成功
- [ ] `uv run pytest -q` 成功
- [ ] KnowledgeBase CRUD
- [ ] Document / Version CRUD
- [ ] Ingestion 状态流转
- [ ] AgentVersion Knowledge Config
- [ ] Owner / RBAC 前置过滤
- [ ] Retrieval contract
- [ ] Context Assembly
- [ ] Citation
- [ ] Retrieval / Runtime Observability
- [ ] Runtime Knowledge Scenario 全链路成功

## Frontend

- [ ] API tests
- [ ] KnowledgeWorkbench tests
- [ ] 历史 View tests 与 canonical 页面路径一致
- [ ] `npm test` 全量成功
- [ ] `npm run build` 成功
- [ ] `src/` 无业务 `.js` / `.jsx` 源码
- [ ] 无测试通过但生产构建失败的问题

## 联调

- [ ] Auth
- [ ] Knowledge
- [ ] Document
- [ ] Version
- [ ] Ingest
- [ ] AgentVersion
- [ ] Runtime Chat
- [ ] Citation
- [ ] Audit / Observability

## 提交

- [ ] 开发文档更新
- [ ] 验收记录更新
- [ ] 仅提交必要源码、测试、迁移和文档
- [ ] 直接提交 `main`
