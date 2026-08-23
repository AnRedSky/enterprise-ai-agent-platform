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

**Phase 2.3 — Model Provider Governance，进行中。**

2.3-A / B / C / D / E / F 已实现并完成对应验收；当前推进 **2.3-G Cost / Usage Accounting**。2.3-G 已提交 PostgreSQL usage/cost 持久化、查询 API、Migration 与 Real API 验证脚本，等待开发者本地执行 acceptance gate。

## 当前 2.3-F 验证结果

```text
Targeted runtime governance tests: 33 passed
Backend Regression: 351 passed, 34 deselected
Alembic head: passed
Tenant Safe Real API Gate: 34 passed
```

以上来自开发者本地实际执行结果，不使用 GitHub Actions 作为验收依据。

## 当前 2.3-G 验证要求

```text
Targeted usage accounting tests
        ↓
Backend Regression
        ↓
Alembic upgrade head
        ↓
Tenant Safe Real API Gate
```

2.3-G 在开发者本地实际通过前不得标记为 Passed。

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
