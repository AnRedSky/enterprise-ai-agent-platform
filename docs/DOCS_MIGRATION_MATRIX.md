# Docs 文档治理重构迁移矩阵

> 基线：远端 `main`（2026-08-21）
>
> 本文是本次 Docs Governance Refactor 的第一阶段产物。先建立迁移矩阵，再执行目录与文档实际迁移。矩阵依据 `docs/` 当前目录清单及已读取的文档正文/阶段记录建立；不会因为文件名相似而直接重命名。

## 1. 新治理结构

```text
docs/
├── README.md
├── PROJECT_STATUS.md
├── 00-architecture/
├── 01-governance/
├── 02-phases/
├── 03-acceptance/
└── 04-errors/
```

规则：

- `PROJECT_STATUS.md`：唯一当前状态入口。
- `00-architecture/`：长期架构与领域/运行时设计。
- `01-governance/`：长期工程与文档治理规则。
- `02-phases/`：每个 Phase 一个正式计划文档；同一 Phase 的任务设计合并进入 Phase 文档，不再用连续数字文件名承载任务历史。
- `03-acceptance/`：每个已验收 Phase 一个正式 Acceptance 文档；子任务验收作为对应 Phase Acceptance 的章节/矩阵。
- `04-errors/`：已经发生并完成分析的工程错误；统一 `ERR-####-description.md` 命名。

## 2. 迁移动作定义

- **MERGE**：正文内容合并到新的单一正式文档，保留设计/事实，不保留旧文件。
- **REWRITE**：内容有效但需要按新职责边界重写。
- **SPLIT**：同一旧文档同时包含多个职责，按内容拆分到不同新文档。
- **ARCHIVE-IN-ACCEPTANCE**：历史任务记录不单独保留为根级文档，合并进对应 Phase Acceptance 的历史任务/验收章节。
- **ERROR-MOVE**：错误记录迁移到 `04-errors/`，保留错误编号与正文事实。
- **STATUS-MERGE**：历史进度内容只合并到 `PROJECT_STATUS.md` 的必要历史摘要，不保留第二个状态源。

## 3. 根级旧文档迁移矩阵

| 旧文档 | 新位置 | 动作 | 说明 |
|---|---|---|---|
| `00-企业级应用 AI 智能体系统完整开发架构与实施流程.md` | `00-architecture/SYSTEM_ARCHITECTURE.md` | MERGE | 总体建设目标、分层架构、Agent Runtime、Model Gateway、Tool、Knowledge、Memory 等长期架构内容；删除原连续编号前缀。 |
| `01-project-initialization.md` | `00-architecture/SYSTEM_ARCHITECTURE.md` + `01-governance/DEVELOPMENT.md` | SPLIT | 初始化事实/技术基线归架构；开发初始化规则归治理；不再作为独立历史入口。 |
| `02-phase-1.2-foundation.md` | `02-phases/PHASE_1_2.md` | MERGE | Phase 1.2 基础平台阶段计划/范围。 |
| `03-phase-1.3-model-gateway.md` | `02-phases/PHASE_1_3.md` | MERGE | Model Gateway Contract 与 Phase 1.3 范围。 |
| `04-phase-1.3-tool-runtime.md` | `02-phases/PHASE_1_3.md` | MERGE | Tool Runtime 设计并入 Phase 1.3。 |
| `05-phase-1.3-tool-runtime-validation.md` | `03-acceptance/PHASE_1_3_ACCEPTANCE.md` | MERGE | Tool Runtime 验收内容并入 Phase 1.3 Acceptance。 |
| `06-phase-1.3-memory.md` | `02-phases/PHASE_1_3.md` | MERGE | Memory 设计并入 Phase 1.3。 |
| `07-project-development-plan.md` | `02-phases/` + `PROJECT_STATUS.md` | SPLIT | 阶段规划归 Phase；当前状态仅保留在 Project Status。 |
| `08-ci-pause-and-main-baseline.md` | `01-governance/DEVELOPMENT.md` | MERGE | main 基线与 CI 开发规则归工程治理；历史事件不再作为独立规则源。 |
| `09-memory-runtime-integration.md` | `02-phases/PHASE_1_3.md` / `03-acceptance/PHASE_1_3_ACCEPTANCE.md` | SPLIT | 设计归 Phase，实际完成/验证归 Acceptance。 |
| `10-memory-governance.md` | `02-phases/PHASE_1_3.md` + `01-governance/DEVELOPMENT.md` | SPLIT | Memory 领域设计归 Phase；长期治理规则归治理。 |
| `11-manual-test-scenarios.md` | `01-governance/LOCAL_TESTING.md` | MERGE | 测试入口与重复场景统一到本地测试治理；若为阶段专属验收则并入对应 Acceptance。 |
| `11-memory-governance-completion.md` | `03-acceptance/PHASE_1_3_ACCEPTANCE.md` | ARCHIVE-IN-ACCEPTANCE | 已完成记录并入 Phase 1.3 Acceptance。 |
| `11-phase-1.4-knowledge-rag-plan.md` | `02-phases/PHASE_1_4.md` | MERGE | Phase 1.4 RAG 计划。 |
| `11-testing-script-governance.md` | `01-governance/DEVELOPMENT.md` | MERGE | 测试脚本职责并入工程开发规则。 |
| `12-observability.md` | `00-architecture/OBSERVABILITY_ARCHITECTURE.md` | MERGE | 长期 Observability 架构。 |
| `12-phase-1.4-e-retrieval-baseline.md` | `02-phases/PHASE_1_4.md` | MERGE | Phase 1.4-E Retrieval baseline。 |
| `12-phase-1.4-e-vector-retrieval-provider.md` | `02-phases/PHASE_1_4.md` | MERGE | Provider 设计并入 Phase 1.4。 |
| `12-phase-1.7-a-02-scheduled-trigger-runtime.md` | `02-phases/PHASE_1_7.md` | MERGE | 1.7-A-02 任务设计。 |
| `12-project-repository-and-environment.md` | `01-governance/DEVELOPMENT.md` + `README.md` | SPLIT | 仓库/环境规则归治理；导航信息归 docs README。 |
| `13-next-step-baseline.md` | `PROJECT_STATUS.md` | STATUS-MERGE | 只保留真实下一步状态，不再建立第二状态源。 |
| `13-observability-completion.md` | `03-acceptance/PHASE_1_3_ACCEPTANCE.md` | ARCHIVE-IN-ACCEPTANCE | Observability 完成记录。 |
| `13-phase-1.4-e-vector-retrieval-validation.md` | `03-acceptance/PHASE_1_4_ACCEPTANCE.md` | MERGE | Retrieval validation。 |
| `13-phase-1.4-f-hybrid-retrieval.md` | `02-phases/PHASE_1_4.md` | MERGE | Hybrid retrieval 设计。 |
| `13-phase-1.5-workflow-governance-plan.md` | `02-phases/PHASE_1_5.md` | MERGE | Phase 1.5 正式阶段计划。 |
| `13-phase-1.7-a-03-scheduled-trigger-governance-recovery.md` | `02-phases/PHASE_1_7.md` | MERGE | 1.7-A-03 任务记录。 |
| `13-phase-1.7-b-scheduler-execution-persistence.md` | `02-phases/PHASE_1_7.md` | MERGE | 1.7-B 设计。 |
| `14-development-command-reference.md` | `01-governance/DEVELOPMENT.md` | MERGE | 开发命令归治理。 |
| `14-phase-1.4-e-provider-validation-checkpoint.md` | `03-acceptance/PHASE_1_4_ACCEPTANCE.md` | MERGE | Provider validation checkpoint。 |
| `14-phase-1.5-g-circuit-breaker.md` | `02-phases/PHASE_1_5.md` + `03-acceptance/PHASE_1_5_ACCEPTANCE.md` | SPLIT | Circuit Breaker 设计归 Phase；实际结果归 Acceptance。 |
| `14-project-compliance-audit-and-correction-plan.md` | `01-governance/DOCUMENTATION.md` + `PROJECT_STATUS.md` | SPLIT | 文档/工程治理整改规则归治理；历史整改状态归项目状态摘要。 |
| `14-tool-runtime-orchestration.md` | `00-architecture/RUNTIME_ARCHITECTURE.md` | MERGE | Tool Runtime orchestration 长期设计。 |
| `15-knowledge-integration-checklist.md` | `02-phases/PHASE_1_4.md` + `03-acceptance/PHASE_1_4_ACCEPTANCE.md` | SPLIT | checklist 设计与实际结果分离。 |
| `15-phase-1.4-e-mock-embedding-validation.md` | `03-acceptance/PHASE_1_4_ACCEPTANCE.md` | MERGE | 专项验证记录。 |
| `15-phase-1.6-workflow-production-hardening-plan.md` | `02-phases/PHASE_1_6.md` | MERGE | Phase 1.6 正式计划。 |
| `15-tool-runtime-completion.md` | `03-acceptance/PHASE_1_3_ACCEPTANCE.md` | ARCHIVE-IN-ACCEPTANCE | Tool Runtime 完成记录。 |
| `16-phase-1.6-b-frontend-workflow-governance-ui-contract.md` | `02-phases/PHASE_1_6.md` | MERGE | 1.6-B Contract。 |
| `16-tool-runtime-integration.md` | `03-acceptance/PHASE_1_3_ACCEPTANCE.md` | ARCHIVE-IN-ACCEPTANCE | Tool Runtime integration 结果。 |
| `17-phase-1.6-c-frontend-backend-e2e-contract.md` | `02-phases/PHASE_1_6.md` + `03-acceptance/PHASE_1_6_ACCEPTANCE.md` | SPLIT | E2E contract 与实际验收分离。 |
| `17-tool-runtime-integration-completion.md` | `03-acceptance/PHASE_1_3_ACCEPTANCE.md` | ARCHIVE-IN-ACCEPTANCE | 完成记录。 |
| `18-phase-1.7-workflow-trigger-scheduling-contract.md` | `02-phases/PHASE_1_7.md` | MERGE | Phase 1.7 总计划。 |
| `18-tool-runtime-e2e-security.md` | `03-acceptance/PHASE_1_3_ACCEPTANCE.md` | ARCHIVE-IN-ACCEPTANCE | 历史 Tool E2E 安全验收。 |
| `19-phase-1.7-c-schedule-governance-frontend-integration.md` | `02-phases/PHASE_1_7.md` | MERGE | 1.7-C。 |
| `19-tool-runtime-e2e-completion.md` | `03-acceptance/PHASE_1_3_ACCEPTANCE.md` | ARCHIVE-IN-ACCEPTANCE | Tool E2E 完成。 |
| `20-phase-1.7-d-browser-frontend-backend-e2e.md` | `02-phases/PHASE_1_7.md` + `03-acceptance/PHASE_1_7_ACCEPTANCE.md` | SPLIT | E2E contract 与结果分离。 |
| `20-runtime-observability-governance.md` | `00-architecture/OBSERVABILITY_ARCHITECTURE.md` | MERGE | 长期 Observability 治理设计。 |
| `21-runtime-observability-governance-completion.md` | `03-acceptance/PHASE_1_3_ACCEPTANCE.md` | ARCHIVE-IN-ACCEPTANCE | 历史 Observability 完成记录。 |
| `22-runtime-management-api-vue-integration.md` | `02-phases/PHASE_1_3.md` + `03-acceptance/PHASE_1_3_ACCEPTANCE.md` | SPLIT | 设计与验收结果分离。 |
| `23-phase-22-completion.md` | `03-acceptance/HISTORICAL_RUNTIME_MANAGEMENT.md` | ARCHIVE-IN-ACCEPTANCE | 历史 Phase 22 记录，不升级为当前 Phase。 |
| `24-phase-23-plan.md` | `02-phases/HISTORICAL_PHASE_23.md` | MERGE | 明确标记为历史规划，避免与当前 1.x Phase 状态冲突。 |
| `25-phase-23-task-01-completion.md` | `03-acceptance/HISTORICAL_PHASE_23.md` | ARCHIVE-IN-ACCEPTANCE | 历史 Task 01。 |
| `26-phase-23-task-02-plan.md` | `02-phases/HISTORICAL_PHASE_23.md` | MERGE | 历史 Task 02 计划。 |
| `27-phase-23-task-02-completion.md` | `03-acceptance/HISTORICAL_PHASE_23.md` | ARCHIVE-IN-ACCEPTANCE | 历史 Task 02 完成。 |
| `28-phase-23-task-03-plan.md` | `02-phases/HISTORICAL_PHASE_23.md` | MERGE | 历史 Task 03 计划。 |
| `29-phase-23-task-03-completion.md` | `03-acceptance/HISTORICAL_PHASE_23.md` | ARCHIVE-IN-ACCEPTANCE | 历史 Task 03 完成。 |
| `30-phase-23-task-04-plan.md` | `02-phases/HISTORICAL_PHASE_23.md` | MERGE | 历史 Task 04 计划。 |
| `31-phase-23-task-04-completion.md` | `03-acceptance/HISTORICAL_PHASE_23.md` | ARCHIVE-IN-ACCEPTANCE | 历史 Task 04 完成。 |
| `32-phase-23-task-05-plan.md` | `02-phases/HISTORICAL_PHASE_23.md` | MERGE | 历史 Task 05 计划。 |
| `36-project-progress-assessment.md` | `PROJECT_STATUS.md` 的历史审计附录 | STATUS-MERGE | 与当前状态存在明显时序差异，不能作为当前状态源；保留其评估事实但标注历史基线。 |
| `37-phase-23-task-06-http-rbac-implementation.md` | `03-acceptance/HISTORICAL_PHASE_23.md` | ARCHIVE-IN-ACCEPTANCE | 历史 Task 06。 |
| `38-phase-23-task-07-validation-plan.md` | `02-phases/HISTORICAL_PHASE_23.md` | MERGE | 历史 Task 07。 |
| `39-manual-test-execution-guide.md` | `01-governance/LOCAL_TESTING.md` | MERGE | 本地测试执行说明。 |
| `40-phase-23-completion-and-phase-24-plan.md` | `03-acceptance/HISTORICAL_PHASE_23.md` + `02-phases/HISTORICAL_PHASE_24.md` | SPLIT | Phase 23 完成与 Phase 24 计划分离。 |
| `41-phase-23-task-07-test-failure-fix.md` | `04-errors/` | ERROR-MOVE | 测试失败修复事实属于工程错误记录。 |
| `41-phase-23-task-07a-frontend-build-fix.md` | `04-errors/` | ERROR-MOVE | Frontend build 修复属于工程错误记录。 |
| `42-phase-23-task-07b-frontend-test-plan.md` | `02-phases/HISTORICAL_PHASE_23.md` | MERGE | 历史测试计划。 |
| `42-phase-23-task-08-plan.md` | `02-phases/HISTORICAL_PHASE_23.md` | MERGE | 历史 Task 08。 |
| `43-phase-23-task-07b-build-fix.md` | `04-errors/` | ERROR-MOVE | build fix。 |
| `43-phase-23-task-08-completion.md` | `03-acceptance/HISTORICAL_PHASE_23.md` | ARCHIVE-IN-ACCEPTANCE | 历史完成。 |
| `44-phase-23-task-07c-frontend-test-plan.md` | `02-phases/HISTORICAL_PHASE_23.md` | MERGE | 历史测试计划。 |
| `44-phase-23-task-09-plan.md` | `02-phases/HISTORICAL_PHASE_23.md` | MERGE | 历史 Task 09。 |
| `45-phase-23-task-09-frontend-runner.md` | `02-phases/HISTORICAL_PHASE_23.md` | MERGE | 历史 runner 设计。 |
| `47-phase-24-task-01-backend-pytest-import-fix.md` | `04-errors/` | ERROR-MOVE | Backend 测试错误/修复。 |
| `48-phase-24-task-02-backend-runtime-tool-memory-validation-plan.md` | `02-phases/HISTORICAL_PHASE_24.md` | MERGE | 历史 Phase 24 计划。 |
| `49-phase-24-task-01-backend-compatibility-fix.md` | `04-errors/` | ERROR-MOVE | Backend compatibility fix。 |
| `50-phase-24-task-02-backend-runtime-validation-plan.md` | `02-phases/HISTORICAL_PHASE_24.md` | MERGE | 历史 Phase 24 计划。 |
| `51-phase-24-task-02-uv-environment-fix.md` | `04-errors/` | ERROR-MOVE | uv 环境问题。 |
| `API_SCENARIO_SMOKE_TEST.md` | `01-governance/LOCAL_TESTING.md` | MERGE | API smoke test 入口。 |
| `API_UNIT_TESTING.md` | `01-governance/LOCAL_TESTING.md` | MERGE | API testing 规范。 |
| `ARCHITECTURE.md` | `00-architecture/SYSTEM_ARCHITECTURE.md` | MERGE | 与总体架构文档合并，保留当前实际实现架构。 |
| `CONTRIBUTING.md` | `01-governance/DEVELOPMENT.md` | MERGE | 当前分支规则与 DEVELOPMENT 冲突，以 DEVELOPMENT 为准，冲突内容不保留。 |
| `DEVELOPMENT-LOCAL-TESTING.md` | `01-governance/LOCAL_TESTING.md` | MERGE | 本地测试规则统一。 |
| `DEVELOPMENT.md` | `01-governance/DEVELOPMENT.md` | REWRITE | 迁移为唯一长期工程规则源，并移除根级旧位置。 |
| `DEVELOPMENT_GUIDELINES.md` | `01-governance/DEVELOPMENT.md` + `01-governance/DOCUMENTATION.md` | SPLIT | 与 DEVELOPMENT 存在冲突；长期规则以 DEVELOPMENT 为准，文档职责规则进入 DOCUMENTATION。 |
| `LOCAL_TESTING.md` | `01-governance/LOCAL_TESTING.md` | REWRITE | 统一本地测试入口，移除过时的 Full Regression 叙述。 |
| `PHASE_1_3_ACCEPTANCE.md` | `03-acceptance/PHASE_1_3_ACCEPTANCE.md` | MOVE | 已是正确命名，只迁移目录。 |
| `PHASE_1_4_D_ACCEPTANCE.md` | `03-acceptance/PHASE_1_4_ACCEPTANCE.md` | MERGE | D 子阶段验收并入 Phase 1.4 总验收。 |
| `PHASE_1_4_FG_ACCEPTANCE.md` | `03-acceptance/PHASE_1_4_ACCEPTANCE.md` | MERGE | F/G 子阶段验收并入 Phase 1.4 总验收。 |
| `PHASE_1_8.md` | `02-phases/PHASE_1_8.md` | MOVE | 当前正式 Phase 文档，只迁移目录并更新内部链接。 |
| `PHASE_1_8_ACCEPTANCE.md` | `03-acceptance/PHASE_1_8_ACCEPTANCE.md` | MOVE | 当前正式 Acceptance，只迁移目录并更新链接。 |
| `PROJECT_REPOSITORY.md` | `README.md` | MERGE | 仓库入口信息并入文档导航。 |
| `PROJECT_STATUS.md` | `PROJECT_STATUS.md` | REWRITE | 保持根级唯一状态入口，修正旧路径和历史冲突。 |

## 4. 已有错误目录

`docs/error-tracking/` 现有错误记录整体迁移到 `docs/04-errors/`，不删除错误事实；文件统一改为：

```text
ERR-0001-<description>.md
ERR-0002-<description>.md
...
```

现有错误编号可能存在重复（例如 `002`、`003`、`004`），迁移时保留原编号作为历史字段，同时重新分配唯一正式 `ERR-####` 编号，建立旧编号映射表。

## 5. `phase-1-5-f/` 目录

以下 4 个子任务记录均并入 `02-phases/PHASE_1_5.md` / `03-acceptance/PHASE_1_5_ACCEPTANCE.md`，不保留独立子目录：

- `001-workflow-execution-ui.md`
- `002-workflow-runtime-tenant-scope.md`
- `003-workflow-runtime-observability.md`
- `004-workflow-execution-governance-controls.md`

## 6. 特别核查结论

1. `DEVELOPMENT.md` 与 `DEVELOPMENT_GUIDELINES.md` 存在实质冲突：前者明确禁止 Full Regression Gate，后者仍要求 `01_full_regression_gate.ps1`。迁移时以 `DEVELOPMENT.md` 为唯一工程准则，并把冲突作为文档治理整改项。fileciteturn10file0L2-L2 fileciteturn11file0L2-L2
2. `CONTRIBUTING.md` 仍要求 feature 分支和 CI/PR 流程，与当前 `DEVELOPMENT.md` 的 main-only 规则冲突；迁移时不能机械合并，必须删除冲突规则。fileciteturn13file0L2-L2
3. `LOCAL_TESTING.md` 与当前治理规则存在历史差异，例如仍描述 Full Regression；迁移后应只保留与 `DEVELOPMENT.md` 一致的独立 Backend / Frontend / Browser Gate。fileciteturn14file0L2-L2
4. `PROJECT_STATUS.md` 当前声称 Phase 1.8 已正式关闭，并明确当前状态与下一阶段入口；因此历史 `Phase 23/24` 文档不能直接覆盖当前状态，必须作为历史资料迁移。fileciteturn8file0L2-L2
5. Phase 1.8 Plan / Acceptance 已经符合“计划 vs 实际验收”分离原则，主要问题是所在目录和旧文档引用；应优先迁移而不是重写事实。fileciteturn15file0L2-L2 fileciteturn16file0L2-L2
6. Phase 1.3/1.4 存在多个子阶段文档和 Acceptance 文档，需要合并成 Phase 级单一正式文档，否则会继续形成第二套阶段编号体系。fileciteturn17file0L2-L2 fileciteturn18file0L2-L2 fileciteturn19file0L2-L2
7. `36-project-progress-assessment.md` 的状态明显早于当前 `PROJECT_STATUS.md`，其内容不能作为当前状态来源；应保留为历史审计材料。fileciteturn24file0L2-L2

## 7. 执行顺序

1. 提交本迁移矩阵。
2. 创建新目录及正式入口文档。
3. 合并/重写正文，保留事实，不伪造测试结果。
4. 全仓更新 `docs/` 引用。
5. 删除旧根级文档、旧 `error-tracking/`、旧 `phase-1-5-f/`。
6. 做文档路径/引用/命名静态检查。
7. 更新 `PROJECT_STATUS.md` 记录 Docs Governance Refactor。
8. 提交 `main`。

本矩阵本身不代表所有迁移已经完成；迁移完成后必须再次检查旧路径是否仍被引用。