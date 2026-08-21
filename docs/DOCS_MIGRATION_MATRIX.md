# Docs Governance Migration Matrix

> 基线：远端 `main`。本矩阵记录本次 Docs Governance Refactor 的实际迁移结果。迁移原则是先读取内容、判断职责，再归并；不是按文件名机械重命名。

## 1. 正式目录

```text
docs/
├── README.md
├── PROJECT_STATUS.md
├── DOCS_MIGRATION_MATRIX.md
├── 00-architecture/
├── 01-governance/
├── 02-phases/
├── 03-acceptance/
└── 04-errors/
```

## 2. Phase 1.2 / 1.3

| Legacy | Canonical | 处理 |
|---|---|---|
| `01-project-initialization.md` | `01-governance/DEVELOPMENT_HISTORY.md` + `02-phases/PHASE_1_2.md` | 内容按历史/阶段职责拆分 |
| `02-phase-1.2-foundation.md` | `02-phases/PHASE_1_2.md` | 归并 |
| `03-phase-1.3-model-gateway.md` | `02-phases/PHASE_1_3.md` | 归并 |
| `04-phase-1.3-tool-runtime.md` | `02-phases/PHASE_1_3.md` | 归并 |
| `05-phase-1.3-tool-runtime-validation.md` | `03-acceptance/PHASE_1_3_ACCEPTANCE.md` | 计划与验收分离 |
| `06-phase-1.3-memory.md` | `02-phases/PHASE_1_3.md` | 归并 |
| `09-memory-runtime-integration.md` | `03-acceptance/PHASE_1_3_ACCEPTANCE.md` / `02-phases/PHASE_1_3.md` | 归并 |
| `10-memory-governance.md` | `02-phases/PHASE_1_3.md` | 归并 |
| `11-memory-governance-completion.md` | `03-acceptance/PHASE_1_3_ACCEPTANCE.md` | 归并 |
| `12-observability.md` | `02-phases/PHASE_1_3.md` | 归并 |
| `13-observability-completion.md` | `03-acceptance/PHASE_1_3_ACCEPTANCE.md` | 归并 |

## 3. Phase 1.4

| Legacy | Canonical | 处理 |
|---|---|---|
| `11-phase-1.4-knowledge-rag-plan.md` | `02-phases/PHASE_1_4.md` | 归并 |
| `12-phase-1.4-e-retrieval-baseline.md` | `02-phases/PHASE_1_4.md` + Acceptance | 归并 |
| `12-phase-1.4-e-vector-retrieval-provider.md` | `02-phases/PHASE_1_4.md` + Acceptance | 归并 |
| `13-phase-1.4-e-vector-retrieval-validation.md` | `03-acceptance/PHASE_1_4_ACCEPTANCE.md` | 归并 |
| `13-phase-1.4-f-hybrid-retrieval.md` | `02-phases/PHASE_1_4.md` + Acceptance | 归并 |
| `14-phase-1.4-e-provider-validation-checkpoint.md` | Acceptance | 归并 |
| `15-phase-1.4-e-mock-embedding-validation.md` | Acceptance | 归并 |
| `phase-1.4-e-retrieval-evaluation-*.md` | `03-acceptance/PHASE_1_4_ACCEPTANCE.md` | 历史失败/修复归并 |
| `PHASE_1_4_D_ACCEPTANCE.md` / `PHASE_1_4_FG_ACCEPTANCE.md` | `03-acceptance/PHASE_1_4_ACCEPTANCE.md` | 合并为唯一 Acceptance |

## 4. Phase 1.5

| Legacy | Canonical | 处理 |
|---|---|---|
| `13-phase-1.5-workflow-governance-plan.md` | `02-phases/PHASE_1_5.md` | 归并 |
| `14-phase-1.5-g-circuit-breaker.md` | `02-phases/PHASE_1_5.md` + Acceptance | 归并 |
| `phase-1.5-d-workflow-runtime-integration.md` | `02-phases/PHASE_1_5.md` | 归并 |
| `phase-1.5-e-governance-audit-trace.md` | `02-phases/PHASE_1_5.md` | 归并 |
| `phase-1.5-f-vue-workflow-governance.md` | `02-phases/PHASE_1_5.md` | 归并 |
| `phase-1-5-f/*.md` | `02-phases/PHASE_1_5.md` | F 子任务归并 |

## 5. Phase 1.6

| Legacy | Canonical | 处理 |
|---|---|---|
| `15-phase-1.6-workflow-production-hardening-plan.md` | `02-phases/PHASE_1_6.md` | 归并 |
| `16-phase-1.6-b-frontend-workflow-governance-ui-contract.md` | `02-phases/PHASE_1_6.md` | 归并 |
| `17-phase-1.6-c-frontend-backend-e2e-contract.md` | `03-acceptance/PHASE_1_6_ACCEPTANCE.md` | 验收归并 |
| 独立 `1.6-D` 文档 | 无 | 完整 tree 未发现，不补造 |

## 6. Phase 1.7

| Legacy | Canonical | 处理 |
|---|---|---|
| `18-phase-1.7-workflow-trigger-scheduling-contract.md` | `02-phases/PHASE_1_7.md` | 归并 |
| `12-phase-1.7-a-02-*` | `02-phases/PHASE_1_7.md` | A-02 归并 |
| `13-phase-1.7-a-03-*` | `02-phases/PHASE_1_7.md` | A-03 归并 |
| `13-phase-1.7-b-*` | `02-phases/PHASE_1_7.md` | B 归并 |
| `19-phase-1.7-c-*` | `02-phases/PHASE_1_7.md` | C 归并 |
| `20-phase-1.7-d-*` | `03-acceptance/PHASE_1_7_ACCEPTANCE.md` | D 验收归并 |
| 独立 A-01/A-04 文档 | 无 | 完整 tree 未发现，不补造 |

## 7. 历史 Phase 14–24

| Legacy 范围 | Canonical | 处理 |
|---|---|---|
| `14-*` ～ `23-*` Tool Runtime / Observability / Runtime Management | `02-phases/HISTORICAL_PHASE_14_22.md` + Acceptance | 按领域演进归并 |
| `24-*` ～ `45-*` Phase 23 历史任务 | `02-phases/HISTORICAL_PHASE_23.md` + Acceptance | 逐份核对后归并 |
| `47-*` ～ `51-*` Phase 24 历史任务 | `02-phases/HISTORICAL_PHASE_24.md` + Acceptance | 逐份核对后归并 |
| 当前 tree 中不存在的旧矩阵路径 | 不创建 | 不凭空补造 |

## 8. Error Tracking

旧 `docs/error-tracking/` 共 17 条 Legacy error 记录，已逐份核对并迁移为：

```text
ERR-0001 ... ERR-0017
```

正式入口：`docs/04-errors/`。每条正文保留 Legacy ID；旧 `error-tracking/` 已删除。

## 9. 通用根级文档

| Legacy | Canonical | 处理 |
|---|---|---|
| `00-企业级应用...md` | `00-architecture/SYSTEM_ARCHITECTURE.md` | 架构内容归并 |
| `ARCHITECTURE.md` | `00-architecture/SYSTEM_ARCHITECTURE.md` | 合并 |
| `CONTRIBUTING.md` | `01-governance/DEVELOPMENT.md` | 有效规则归并；旧 feature/PR 规则废止 |
| `DEVELOPMENT.md` | `01-governance/DEVELOPMENT.md` | canonical 已迁移 |
| `DEVELOPMENT_GUIDELINES.md` | `01-governance/DEVELOPMENT.md` | 冲突规则不继承 |
| `DEVELOPMENT-LOCAL-TESTING.md` / `LOCAL_TESTING.md` | `01-governance/LOCAL_TESTING.md` | 合并 |
| `API_SCENARIO_SMOKE_TEST.md` / `API_UNIT_TESTING.md` | `01-governance/API_TESTING.md` | 合并 |
| `PROJECT_REPOSITORY.md` / `12-project-repository-and-environment.md` | `01-governance/DEVELOPMENT_HISTORY.md` / `DEVELOPMENT.md` | 合并 |
| `PHASE_1_3_ACCEPTANCE.md` | `03-acceptance/PHASE_1_3_ACCEPTANCE.md` | canonical 已迁移 |
| `PHASE_1_8.md` / `PHASE_1_8_ACCEPTANCE.md` | `02-phases/PHASE_1_8.md` / `03-acceptance/PHASE_1_8_ACCEPTANCE.md` | canonical 已迁移 |

## 10. 最终状态

截至本矩阵更新：

- `docs/` 根级旧连续编号文档已删除。
- `docs/error-tracking/` 已删除。
- 新文档只允许进入五层结构 + `PROJECT_STATUS.md`。
- 旧文档中的历史事实已经归并到 Phase / Acceptance / Governance History / Error records。
- 未发现的历史文档不凭空补造。
- 后续新 Phase 只能使用 `PHASE_x_y.md` / `PHASE_x_y_ACCEPTANCE.md`。
