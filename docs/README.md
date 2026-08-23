# 文档中心

本目录采用统一的 Docs Governance 结构。旧的连续数字文件名已经完成迁移并从 `docs/` 根目录删除；不再作为新文档命名方式。

## 当前入口

1. `PROJECT_STATUS.md`：唯一当前项目状态入口。
2. `01-governance/DEVELOPMENT.md`：唯一长期工程开发规则。
3. `01-governance/DOCUMENTATION.md`：唯一文档治理规则。
4. `02-phases/`：阶段计划与明确标记的历史 Phase。
5. `03-acceptance/`：阶段验收与历史验收证据。
6. `04-errors/`：工程错误。
7. `00-architecture/`：长期架构。

## 当前开发阶段

**无进行中的正式 Phase。Phase 2.3 — Model Provider Governance 已正式关闭。**

2.3-A / B / C / D / E / F / G 均已完成对应本地验收。当前下一项正式工作不是直接编码 Scheduler，而是确认 **Phase 2.4 Durable Scheduler Contract**；Contract 未确认前，不创建 Scheduler Migration 或业务代码。

## Phase 2.3 最终本地验收结果

```text
Targeted usage/governance tests: 40 passed
Backend Regression: 358 passed, 35 deselected
Alembic upgrade heads: passed
Alembic current: 0023_model_usage_accounting (head), 0027_retrieval_evaluation_vector_space (head)
Tenant Safe Real API Gate: 35 passed
```

以上结果来自开发者本地实际执行，不使用 GitHub Actions 作为开发测试、质量门禁或验收依据。

## Phase 2.4 进入条件

正式进入代码开发前必须确认：

1. `next_run_at` 的计算、时区与时钟语义；
2. 多实例 scheduler lease / ownership 语义；
3. lease 过期、抢占与重复执行边界；
4. misfire policy 与可接受延迟；
5. 执行幂等键与重复触发语义；
6. paused / enabled / disabled 状态转换；
7. 调度状态与 WorkflowExecution 的审计、trace 关系；
8. PostgreSQL migration 与 Real API acceptance 场景。

Contract 确认后，按开发准则进入：

```text
Backend Domain + API Contract
        ↓
PostgreSQL Migration + Backend tests
        ↓
Real API Gate
        ↓
Frontend API Types + Vitest / UI（如范围需要）
        ↓
Browser E2E（如范围需要）
```

## 目录

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

## 阅读顺序

```text
README
  ↓
PROJECT_STATUS
  ↓
当前 PHASE_x_y
  ↓
对应 PHASE_x_y_ACCEPTANCE（如已关闭）
  ↓
DEVELOPMENT / DOCUMENTATION
```

## 文档追溯链

```text
PROJECT_STATUS
    ↓
PHASE_x_y
    ↓
Task x.y-A/B/C...
    ↓
Code / API / Migration
    ↓
Local Test
    ↓
PHASE_x_y_ACCEPTANCE
```

## 命名规则

- Phase：`PHASE_1_9.md`
- Acceptance：`PHASE_1_9_ACCEPTANCE.md`
- Error：`ERR-0001-description.md`
- Architecture：描述职责，例如 `SYSTEM_ARCHITECTURE.md`、`RUNTIME_ARCHITECTURE.md`
- Governance：`DEVELOPMENT.md`、`DOCUMENTATION.md`、必要的稳定治理专题文档
- 历史阶段：`HISTORICAL_PHASE_14_22.md` 等，只用于保存旧时间线，不得作为当前 Phase 编号

禁止新增 `01-xxx.md`、`12-phase-1.7-xxx.md`、`phase-1.7-xxx.md`、根级 `PHASE_*.md` 这类混合入口。

## 迁移状态

**Docs Governance Refactor 第二阶段已完成。** 已逐份核对并迁移 Phase 1.4、1.5、1.6、1.7、历史 Phase 14–22、23、24，以及旧 `error-tracking`。全仓旧根级 docs 已清理；迁移矩阵保留旧 → 新映射和“未发现内容不补造”的原则。

后续新开发必须从最新 `main` 开始，并先更新 `PROJECT_STATUS.md` / 对应 Phase 文档，再执行代码任务。
