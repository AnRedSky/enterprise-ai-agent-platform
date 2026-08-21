# 文档治理规则

## 1. 目的

本文件定义 `docs/` 的分类、职责、命名、迁移、状态记录和验收规则。工程开发规则仍以 `DEVELOPMENT.md` 为准。

## 2. 正式目录

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

## 3. 职责边界

### PROJECT_STATUS.md

只记录当前状态：当前基线、当前 Phase、已完成、实际测试结果、阻塞、下一步。不得成为历史任务明细仓库。

### 00-architecture/

记录长期稳定的系统、领域、Runtime、数据、安全和 Observability 架构。不得记录单次任务的临时执行结果。

### 01-governance/

记录长期规则。`DEVELOPMENT.md` 是唯一工程开发规则；`DOCUMENTATION.md` 是唯一文档治理规则；本目录可以包含本地测试说明等稳定入口文档，但不能复制工程规则。

### 02-phases/

一个业务/工程 Phase 对应一个正式计划文档：`PHASE_x_y.md`。同一 Phase 的 A/B/C 任务设计、Contract、Scope、验收标准统一进入该 Phase 文档，不再为每个任务创建连续数字根级文件。

### 03-acceptance/

一个已关闭 Phase 对应一个正式验收文档：`PHASE_x_y_ACCEPTANCE.md`。实际执行结果只能在开发者反馈后记录。子任务验收进入 Phase Acceptance 的任务矩阵，不再产生第二套验收文件编号。

### 04-errors/

只记录已经发生并完成分析的工程错误。错误必须有实际现象、根因、影响、修复、验证和防重复措施。

## 4. 命名

```text
PHASE_1_8.md
PHASE_1_8_ACCEPTANCE.md
ERR-0001-real-api-register-500.md
SYSTEM_ARCHITECTURE.md
RUNTIME_ARCHITECTURE.md
DEVELOPMENT.md
DOCUMENTATION.md
```

禁止新增：

```text
01-xxx.md
12-phase-1.7-xxx.md
phase-1.7-xxx.md
completion-xxx.md
validation-xxx.md
```

这些信息应归入 Phase / Acceptance / Error 的正式结构。

## 5. 计划与事实分离

```text
PHASE_x_y.md
    = 计划、设计、Contract、任务拆解、验收标准

PHASE_x_y_ACCEPTANCE.md
    = 实际实施范围、真实测试结果、已知问题、验收结论

PROJECT_STATUS.md
    = 当前状态与下一步
```

不得把未执行测试写成通过；不得把历史状态覆盖当前状态。

## 6. 历史资料

历史 Phase 23/24 等旧编号文档如果与当前 Phase 编号体系存在冲突，不直接删除事实，也不冒充当前 Phase。统一归入 `HISTORICAL_*` 文档，并明确历史基线。

## 7. 错误编号

历史 `docs/error-tracking/` 中存在重复的 `002/003/004` 编号。迁移到 `04-errors/` 时重新分配唯一 `ERR-####`，同时在迁移矩阵中记录旧编号映射。

## 8. 引用规则

文档之间只引用新的正式路径。迁移完成后，全仓搜索旧路径：

```text
12-phase-
13-phase-
14-phase-
phase-1-
error-tracking/
DEVELOPMENT_GUIDELINES.md
```

不得残留正式运行入口引用。

## 9. 修改流程

```text
最新 main
  ↓
读取 docs 全部内容
  ↓
建立迁移矩阵
  ↓
创建新文档
  ↓
合并/重写内容
  ↓
更新引用
  ↓
删除旧入口
  ↓
静态校验
  ↓
更新 PROJECT_STATUS
  ↓
提交 main
```

禁止只根据文件名进行批量重命名。