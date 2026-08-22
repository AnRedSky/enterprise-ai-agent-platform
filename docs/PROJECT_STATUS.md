# Project Status

> 当前项目状态唯一入口。文档治理规则见 `docs/01-governance/DOCUMENTATION.md`，工程开发规则见 `docs/01-governance/DEVELOPMENT.md`。

## 1. 当前基线

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 最新产品基线：Phase 2.1 Enterprise Organization & Access Governance 已完成最终联合验收并正式关闭。
- 开发原则：所有任务直接基于最新 `main`；禁止创建功能分支、临时分支或长期分支。
- 当前开发阶段：**Phase 1.9 已完成 / 正式关闭；Phase 2.1 已完成 / 正式关闭；当前进入 Phase 2.2 Retrieval Production Quality 的 2.2-A Contract。**
- 产品能力基线：`docs/PRODUCT_CAPABILITY_BASELINE.md`
- 产品与功能开发对比矩阵：`docs/PRODUCT_DEVELOPMENT_MATRIX.md`
- 产品整体路线：`docs/PRODUCT_ROADMAP.md`

## 2. Phase 2.1 最终联合验收证据

### Frontend Regression / Build

```text
16 test files passed
69 tests passed
Production build passed
[PASS] Frontend regression gate completed.
```

### Backend Regression

```text
275 passed, 30 deselected in 6.92s
```

### Real API

```text
[1/2] Prepare real API test context
Real API context prepared: .real_api_context_39ad1c1c1d55
[2/2] Execute all real HTTP API tests
30 passed in 39.91s
[PASS] Real API gate completed. Frontend/backend integration may proceed.
```

### Browser E2E

```text
scripts/test/e2e/02_run_organization_e2e.ps1
3 passed (14.2s)
[PASS] Phase 2.1-F organization browser E2E contract completed.

npx playwright test tests/e2e/organization-management.spec.ts --project="Desktop Chrome"
3 passed (12.8s)
```

### Phase 2.1 结论

以上证据共同满足 Phase 2.1 Definition of Done：Contract、Migration、Backend、Real API、Frontend、Browser E2E、成员生命周期、权限边界和 Audit 均已验证。

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
| **Phase 2.2** | **进行中** | Retrieval Production Quality；当前推进 2.2-A Product / Retrieval Quality Contract |
| Phase 2.3～2.8 | 路线候选 | Model Governance、Durable Scheduler、Advanced Workflow、Event Infrastructure、Multi-Agent、Agent Marketplace |

## 4. Phase 2.2 当前任务

### 2.2-A Product / Retrieval Quality Contract — **设计中**

产品路线明确 Phase 2.2 的目标是让企业知识问答具备稳定、可量化的真实语义检索质量；进入实现前必须明确 Provider、数据集、Recall / Precision / Citation 指标。当前只进行 Contract、指标、数据集、失败边界和验收设计，不提前引入 Provider 或数据库实现。

下一步：

1. 读取现有 Knowledge / RAG / Retrieval 架构与 Phase 1.4 历史验收边界。
2. 定义真实 Embedding Provider Contract 与配置边界。
3. 定义固定评测数据集格式、版本和可重复执行方式。
4. 定义 Recall@K、Precision@K、Citation correctness 等指标及最低门槛。
5. 定义离线评估与 Real Provider Gate 的职责边界。
6. 完成 `PHASE_2_2.md` / `PHASE_2_2_ACCEPTANCE.md` 后，再进入实现。

## 5. 维护规则

后续任何功能完成、延期、阻塞、范围变化或新的工程错误，都必须同步：

- `docs/PROJECT_STATUS.md`
- 对应 `docs/02-phases/PHASE_x_y.md`
- 对应 `docs/03-acceptance/PHASE_x_y_ACCEPTANCE.md`
- 已分析完成的工程错误同步 `docs/04-errors/`

同一任务的多份文档变更应作为一个文档变更集一次性提交，避免每个文档形成独立中间提交。
