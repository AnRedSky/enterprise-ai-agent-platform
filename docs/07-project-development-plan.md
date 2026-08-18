# 07 - 项目开发规划

## 1. 项目背景

建设企业级 AI Agent 平台，提供 Agent 配置、版本治理、模型接入、会话、Memory、Tool、Runtime、权限、审计和可观测能力。

## 2. 项目目标

- 建立 FastAPI + Vue 的前后端工程基线。
- 建立可扩展的 Agent Runtime。
- 通过 Model Gateway 解耦模型供应商。
- 建立受治理的 Tool Runtime。
- 建立 Session / Memory 上下文能力。
- 建立 RBAC、审计和 Observability 基础。
- 为后续 Knowledge / RAG / Workflow / Governance 扩展预留边界。

## 3. 技术栈

### Backend

- Python 3.12
- FastAPI
- Pydantic
- SQLAlchemy Async
- Alembic
- PostgreSQL
- Redis
- pytest

### Frontend

- Vue 3
- TypeScript
- Vite
- Element Plus
- Pinia

### Engineering

- GitHub
- GitHub Actions（当前临时暂停自动触发）
- Docker Compose

## 4. 功能模块

1. Identity / Authentication
2. RBAC
3. Agent Registry
4. Agent Version
5. Session / Message
6. Model Gateway
7. Tool Registry / Runtime
8. Memory
9. Observability
10. Vue Admin Console
11. Knowledge / RAG（后续阶段）
12. Workflow / Governance（后续阶段）

## 5. 开发阶段计划

| 阶段 | 内容 | 状态 |
|---|---|---|
| Phase 1.0 | 工程初始化、FastAPI + Vue | 已完成 |
| Phase 1.2 | Identity、RBAC、Agent、Session、SSE、基础 Tool | 已完成 |
| Phase 1.3-A | Model Gateway | 已完成 |
| Phase 1.3-B | Tool Runtime | 基础能力已完成，治理编排待完成 |
| Phase 1.3-C | Memory | 当前阶段 |
| Phase 1.3-D | Observability | 待开始 |
| Phase 1.3-E | Vue 管理端深化 | 待开始 |
| Phase 1.4 | Knowledge / RAG | 后续 |
| Phase 1.5 | Workflow / Governance | 后续 |

## 6. 人员分工

当前项目采用职责域划分，具体人员可按团队实际情况映射：

- Project Owner：需求、范围、里程碑与验收
- Backend：FastAPI、Runtime、Model、Tool、Memory、数据库
- Frontend：Vue 管理端、Agent Console、Debug UI
- QA：单元测试、集成测试、回归测试
- DevOps：Docker、CI/CD、环境和部署
- Security：RBAC、Tool 安全、SSRF、审计和数据安全

## 7. 交付规则

每个功能模块必须同时交付：

1. 源代码
2. 数据库 Migration（如涉及数据结构）
3. 自动化测试
4. 编号开发文档
5. 规范 Git Commit
6. 验收结果与下一步计划

## 8. 分支规则

当前开发统一基于 `main` 最新代码。功能完成后直接形成规范提交；后续如恢复 PR 流程，功能分支必须从最新 `main` 创建。

## 9. Git Commit 规范

采用 Conventional Commits：

- feat
- fix
- refactor
- test
- docs
- chore

提交信息必须说明实现内容或修复细节。

## 10. 禁止提交

严禁提交：

- `.env` / 密钥 / Token
- `node_modules`
- `.venv`
- `__pycache__`
- `dist`
- 日志
- 临时压缩包
- 临时截图
- 个人文件
- 与项目无关的实验文件

## 11. 当前风险

CI 自动执行当前存在不稳定问题，因此暂时关闭 push / pull_request 自动触发；恢复前必须完成失败原因、依赖、测试环境和配置的集中修复与验证。
