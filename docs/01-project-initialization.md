# 01 - 项目初始化与技术选型记录

## 1. 记录性质

这是对项目早期开发工作的补录文档，用于恢复开发历史。内容依据项目启动阶段已确定的技术路线与已实施工程骨架整理，不替代后续正式设计文档。

## 2. 上一阶段

项目尚未形成代码基线，首先需要确定企业级 AI Agent 平台的技术架构与实施方式。

## 3. 当前完成

确定采用：

- Backend：FastAPI + Python
- Frontend：Vue 3 + TypeScript + Vite
- Database：PostgreSQL
- Cache：Redis
- Migration：Alembic
- Test：pytest
- CI：GitHub Actions

项目采用 API、Service、Runtime、Gateway/Tool/Memory、Repository 的分层思路。

## 4. Phase 1 目标

先完成单 Agent、单模型、基础 Tool 的 MVP，建立 Agent Registry、Runtime、Model Gateway、Session/Message 等基础能力，再逐步扩展 Memory、Observability 与治理能力。

## 5. 下一步

进入 Phase 1.2，建设身份认证、RBAC、Agent Registry、Session/Message、SSE 与基础 Model/Tool 能力。
