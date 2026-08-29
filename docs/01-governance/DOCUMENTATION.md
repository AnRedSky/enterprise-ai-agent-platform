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
├── 04-errors/
└── 05-long-term/
```

## 3. 职责边界

### PROJECT_STATUS.md

只记录当前状态：当前基线、当前 Phase、已完成、实际测试结果、阻塞、下一步。不得成为历史任务明细仓库。

### 00-architecture/

记录长期稳定的系统、领域、Runtime、数据、安全、Observability 和 Backend 模块架构。不得记录单次任务的临时执行结果。

### 01-governance/

记录长期规则。`DEVELOPMENT.md` 是唯一工程开发规则；`DOCUMENTATION.md` 是唯一文档治理规则；本目录可以包含本地测试说明等稳定入口文档，但不能复制工程规则。

### 02-phases/

一个业务/工程 Phase 对应一个正式计划文档：`PHASE_x_y.md`。同一 Phase 的 A/B/C 任务设计、Contract、Scope、验收标准统一进入该 Phase 文档，不再为每个任务创建连续数字根级文件。

### 03-acceptance/

一个已关闭 Phase 对应一个正式验收文档：`PHASE_x_y_ACCEPTANCE.md`。实际执行结果只能在开发者反馈后记录。子任务验收进入 Phase Acceptance 的任务矩阵，不再产生第二套验收文件编号。

### 04-errors/

只记录已经发生并完成分析的工程错误。错误必须有实际现象、根因、影响、修复、验证和防重复措施。

### 05-long-term/

只记录当前尚未完成、需要跨多个 Phase 持续推进的长期产品/工程能力。每项长期能力必须使用独立 `LT-xx-*.md` 文档，不能与当前 Phase 计划、Acceptance 或 Error 记录混合。

`05-long-term/README.md` 维护长期任务索引。LT 文档记录目标、当前状态、缺口、边界、依赖、长期拆解和完成判定；只有 Contract 冻结并正式进入开发后，才建立对应 `02-phases/PHASE_x_y.md`。

已关闭 Phase 不因 LT 任务重新打开；已验收 Runtime 只保留回归维护。长期任务中的候选技术不能在 Contract 冻结前写成既定实现。

## 4. Backend 模块化整改测试

模块化整改测试编排统一位于：

```text
backend/scripts/test/module-refactor/
```

当前固定入口：

```text
01_backend_module_refactor_gate.ps1
```

Gate 同时检查旧文件、旧 import、重复实现、目标目录以及 Agent / Knowledge / Infrastructure Provider targeted tests，最终再执行 Backend Regression。测试实现仍必须位于 `backend/tests/unit`、`integration`、`api_contract`、`api_real`，脚本只负责 Gate 和顺序编排。

## 5. 命名

```text
PHASE_1_8.md
PHASE_1_8_ACCEPTANCE.md
ERR-0001-real-api-register-500.md
SYSTEM_ARCHITECTURE.md
RUNTIME_ARCHITECTURE.md
BACKEND_MODULE_ARCHITECTURE.md
BACKEND_MODULE_MIGRATION_MAP.md
DEVELOPMENT.md
DOCUMENTATION.md
LT-01-ENTERPRISE-INTEGRATION-EVENT-INFRASTRUCTURE.md
```

禁止新增：

```text
01-xxx.md
12-phase-1.7-xxx.md
phase-1.7-xxx.md
completion-xxx.md
validation-xxx.md
```

这些信息应归入 Phase / Acceptance / Error / Long-term 的正式结构。

## 6. 计划与事实分离

```text
PHASE_x_y.md
    = 当前正式 Phase 的计划、设计、Contract、任务拆解、验收标准

PHASE_x_y_ACCEPTANCE.md
    = 当前/已关闭 Phase 的实际实施范围、真实测试结果、已知问题、验收结论

PROJECT_STATUS.md
    = 当前状态与下一步

05-long-term/LT-xx-*.md
    = 跨 Phase 的未完成长期能力，不代表当前 Phase 已立项

BACKEND_MODULE_MIGRATION_MAP.md
    = 架构迁移设计、目标映射与迁移规则；不虚构测试事实
```

不得把未执行测试写成通过；不得把历史状态覆盖当前状态；不得把长期 backlog 伪装成当前 Phase 任务。

## 7. 历史资料

历史 Phase 23/24 等旧编号文档如果与当前 Phase 编号体系存在冲突，不直接删除事实，也不冒充当前 Phase。统一归入 `HISTORICAL_*` 文档，并明确历史基线。

## 8. 错误编号

历史 `docs/error-tracking/` 中存在重复的 `002/003/004` 编号。迁移到 `04-errors/` 时重新分配唯一 `ERR-####`，同时在迁移矩阵中记录旧编号映射。

## 9. 引用规则

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

## 10. 修改流程

```text
最新 main
  ↓
读取 docs 全部内容
  ↓
建立迁移矩阵
  ↓
创建/更新长期任务文档（如存在跨 Phase backlog）
  ↓
创建/更新当前 Phase / Acceptance / Error 文档
  ↓
更新引用
  ↓
静态校验
  ↓
一次性形成文档变更集
  ↓
更新 PROJECT_STATUS / Phase / Acceptance
  ↓
以单个原子提交提交 main
```

禁止只根据文件名进行批量重命名。

### 文档变更集规则

同一任务涉及多个文档时，应先完成全部相关文档的评估、修改和交叉引用，再统一提交。典型变更集包括：

- `DEVELOPMENT.md` / `DOCUMENTATION.md` 治理规则调整；
- 当前 `PROJECT_STATUS.md`；
- 对应 `PHASE_x_y.md`；
- 对应 `PHASE_x_y_ACCEPTANCE.md`；
- 已分析完成的 `04-errors/`；
- `05-long-term/LT-xx-*.md`；
- 新 Phase 的计划 / Acceptance 文档。

除非测试反馈、代码修复或新的事实变化确实形成新的工程交付单元，否则不得为上述文档分别创建独立提交。
