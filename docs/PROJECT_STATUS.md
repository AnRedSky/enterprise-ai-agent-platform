# Project Status

> 当前项目状态唯一入口。文档治理规则见 `docs/01-governance/DOCUMENTATION.md`，工程开发规则见 `docs/01-governance/DEVELOPMENT.md`。

## 1. 当前基线

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 开发原则：所有任务直接基于最新 `main`，禁止 feature / task / 临时分支。

## 2. 当前阶段

**Docs Governance Refactor — 第二阶段已完成。**

本阶段不是业务代码开发，目标是完成旧 `docs/` 内容的逐份核对、迁移、旧路径清理和最终目录验收。

## 3. 已完成的文档迁移

### Phase 1.4

- Knowledge / RAG plan
- Retrieval baseline
- Vector Provider / validation
- Hybrid Retrieval
- Provider checkpoint
- Mock Embedding validation
- Runtime Knowledge acceptance
- F/G acceptance
- Evaluation runner / mock fixture 历史失败与修复

统一归并到：

```text
docs/02-phases/PHASE_1_4.md
docs/03-acceptance/PHASE_1_4_ACCEPTANCE.md
```

### Phase 1.5

A～G 全部历史计划、Runtime Integration、Governance/Audit/Trace、Frontend Governance、Retry/Deadline/Idempotency、Circuit Breaker、F 子任务均已归并到：

```text
docs/02-phases/PHASE_1_5.md
docs/03-acceptance/PHASE_1_5_ACCEPTANCE.md
```

### Phase 1.6

A～C 历史文档已归并；完整 tree 未发现独立 1.6-D，因此不补造：

```text
docs/02-phases/PHASE_1_6.md
docs/03-acceptance/PHASE_1_6_ACCEPTANCE.md
```

### Phase 1.7

A/B/C/D 历史文档已归并；完整 tree 未发现独立 A-01/A-04 正文，因此不补造：

```text
docs/02-phases/PHASE_1_7.md
docs/03-acceptance/PHASE_1_7_ACCEPTANCE.md
```

### 历史 Phase 14–24

旧连续编号历史已隔离到：

```text
docs/02-phases/HISTORICAL_PHASE_14_22.md
docs/02-phases/HISTORICAL_PHASE_23.md
docs/02-phases/HISTORICAL_PHASE_24.md

docs/03-acceptance/HISTORICAL_PHASE_14_22.md
docs/03-acceptance/HISTORICAL_PHASE_23.md
docs/03-acceptance/HISTORICAL_PHASE_24.md
```

这些历史文档不代表当前项目 Phase。

### Error Tracking

旧 `docs/error-tracking/` 17 条记录已逐份迁移为：

```text
docs/04-errors/ERR-0001...ERR-0017
```

保留 Legacy ID，旧目录已删除。

## 4. 根级 docs 清理

本阶段完成后，`docs/` 根目录只保留：

```text
README.md
PROJECT_STATUS.md
DOCS_MIGRATION_MATRIX.md
00-architecture/
01-governance/
02-phases/
03-acceptance/
04-errors/
```

旧连续编号文档、根级 Phase acceptance、旧 `DEVELOPMENT.md`、旧 `CONTRIBUTING.md`、旧 `API_*`、旧 `ARCHITECTURE.md` 等均已迁移后删除。

GitHub 当前 docs 根目录已不再存在 `01-xxx.md`、`12-phase-*`、`phase-*`、根级 `PHASE_*` 旧入口。

## 5. 文档真实性规则

- 历史计划不等于当前完成。
- 修复代码不等于测试通过。
- 未实际执行的测试不得写 PASS。
- 找不到历史源文档的任务不补造。
- 历史 Phase 不覆盖当前 `PROJECT_STATUS`。
- Error record 保留失败事实，即使已经修复。

## 6. 当前正式阶段状态

| Phase | 状态 |
|---|---|
| Phase 1.0 | 已完成 |
| Phase 1.2 | 已完成 |
| Phase 1.3 | 已完成当前历史范围 |
| Phase 1.4 | 已完成 |
| Phase 1.5 | 已完成 / 正式关闭 |
| Phase 1.6 | 已完成 / 正式关闭 |
| Phase 1.7 | 已完成 / 正式关闭 |
| Phase 1.8 | 已完成 / 正式关闭 |

## 7. Phase 1.8 历史实际结果

原 Phase 1.8 Acceptance 中的实际历史结果继续保留在 canonical Acceptance 文档；本次文档迁移没有重新执行测试，也没有重新推断测试结果。

## 8. 下一步

Docs Governance Refactor 第二阶段已经完成。后续回到正常开发流程：

1. 以最新 `main` 为基线。
2. 从 `PROJECT_STATUS.md` 选择下一项正式任务。
3. 如进入新 Phase，先建立 `docs/02-phases/PHASE_x_y.md`。
4. Backend Contract → Migration/pytest → Frontend → Real API → 独立 Gate → 联调 → Acceptance。
5. 新错误写入 `docs/04-errors/ERR-xxxx-description.md`。
6. 完成后更新 `PROJECT_STATUS.md` 并直接提交 `main`。

## 9. 文档治理入口

- `docs/README.md`
- `docs/DOCS_MIGRATION_MATRIX.md`
- `docs/01-governance/DEVELOPMENT.md`
- `docs/01-governance/DOCUMENTATION.md`
- `docs/01-governance/LOCAL_TESTING.md`
- `docs/01-governance/API_TESTING.md`
