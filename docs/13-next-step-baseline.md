# 下一步开发基线

## 当前阶段

当前项目处于 **Phase 1.4-D Runtime Integration 联调** 阶段。Knowledge Registry、Document ingestion、Retrieval contract、Frontend Knowledge 管理基础能力已经形成，下一步以 Runtime + Knowledge 完整闭环为优先。

## 下一步任务顺序

1. 使用 Backend `uv` 环境执行数据库迁移与 pytest，确保数据库 schema、AgentVersion Knowledge Config 与 Runtime contract 一致。
2. 执行 Runtime Knowledge Scenario：Auth → Knowledge → Document → Version → Ingest → AgentVersion Knowledge Config → Runtime Chat → Citation。
3. 修复 Runtime 中 Knowledge 配置、权限过滤、Context Assembly、Citation 与 Observability 的真实联调问题。
4. 执行 Frontend 全量 `npm test`，修复历史 View Test 与当前 canonical Vue 页面路径不一致的问题。
5. 执行 Frontend `npm run build`，保证 TypeScript 类型检查与 Vite 生产构建均通过。
6. 执行 Backend pytest + Frontend Vitest + Frontend production build 全量回归。
7. 更新开发规划和验收记录。
8. 直接提交 `main`。

## 强制环境规则

Backend：必须在 `backend` 目录通过 `uv run ...` 使用项目虚拟环境；依赖统一由 `uv add` / `uv add --dev` 管理。

Frontend：使用项目 Node/npm 环境；测试与生产构建必须分别执行，不能以单独 Vitest 通过作为完成标准。

## 验收门槛

```text
uv run pytest -q                         PASS
uv run alembic upgrade head              PASS
Runtime Knowledge Scenario                PASS
npm test                                  PASS
npm run build                             PASS
前后端联调                                PASS
开发/验收文档更新                          PASS
```
