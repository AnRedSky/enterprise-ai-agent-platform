# 文档中心

本目录采用统一的 Docs Governance 结构。旧的连续数字文件名仅作为迁移历史，不再作为新文档命名方式。

## 当前入口

1. `PROJECT_STATUS.md`：唯一当前项目状态入口。
2. `01-governance/DEVELOPMENT.md`：唯一长期工程开发规则。
3. `01-governance/DOCUMENTATION.md`：唯一文档治理规则。
4. `02-phases/`：阶段计划。
5. `03-acceptance/`：阶段验收。
6. `04-errors/`：工程错误。
7. `00-architecture/`：长期架构。

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

- Phase：`PHASE_1_8.md`
- Acceptance：`PHASE_1_8_ACCEPTANCE.md`
- Error：`ERR-0001-description.md`
- Architecture：描述职责，例如 `SYSTEM_ARCHITECTURE.md`、`RUNTIME_ARCHITECTURE.md`
- Governance：`DEVELOPMENT.md`、`DOCUMENTATION.md`

禁止新增 `01-xxx.md`、`12-phase-1.7-xxx.md`、`phase-1.7-xxx.md` 这类连续序号/混合命名。

## 迁移状态

本次 Docs Governance Refactor 已先提交迁移矩阵；实际内容迁移、旧路径清理和引用校验必须在矩阵基础上逐项完成，不得仅凭文件名重命名。