# 前端文档索引与记录规范

> 本目录 `frontend/docs` 是前端工程设计、实现、验证和长期规划的唯一文档归档位置之一。项目级工程规则以 `docs/01-governance/DEVELOPMENT.md` 为最高约束；前端具体规则以 `FRONTEND_DEVELOPMENT_GUIDELINES.md` 为准。
>
> 本索引解决历史文档数量增长后的定位、归档、状态追踪和重复记录问题，不删除已有工程证据。历史文档继续保留原路径，后续通过规范化命名逐步收敛。

## 1. 文档分层

| 层级 | 用途 | 代表文档 |
|---|---|---|
| 规范 | 前端长期不变的工程规则 | `FRONTEND_DEVELOPMENT_GUIDELINES.md`、`FRONTEND_UI_TEXT_GUIDELINES.md` |
| 架构 | 信息架构、应用壳、公共 UI 体系 | `ENTERPRISE_UI_INFORMATION_ARCHITECTURE.md`、`APP_SHELL_ENTERPRISE_UI_OPTIMIZATION.md` |
| 计划 | 当前任务、长期路线、测试执行计划 | `FRONTEND_TASK_EXECUTION_PLAN.md`、`FRONTEND_LONG_TERM_ROADMAP.md`、`FRONTEND_PHASED_TESTING_AND_EXECUTION_PLAN.md` |
| P1 主线 | 当前企业级体验深化 | `P1_ENTERPRISE_EXPERIENCE.md`、`P1_1_DEEP_OBSERVABILITY.md`、`P1.2-WORKFLOW-LIFECYCLE-WORKBENCH.md` |
| 功能设计 | 单领域实现与交互设计 | `RUNTIME_EXECUTIONS_UI_IMPLEMENTATION.md`、`AGENT_RUNTIME_DEBUG_ENHANCEMENT.md`、`INTEGRATION_EVENT_CONSOLE.md`、`WEBHOOK_DELIVERY_CONSOLE.md` |
| 回归/修复 | 测试、发布加固、回归问题 | `FINAL_UI_REGRESSION_REMEDIATION.md`、`FINAL_UI_RELEASE_HARDENING.md`、`APP_SHELL_NAVIGATION_REGRESSION.md` |
| 文本治理 | 用户可见文本与迁移记录 | `FRONTEND_UI_TEXT_GUIDELINES.md`、`RUNTIME_UI_TEXT_MIGRATION.md`、`WORKFLOW_UI_TEXT_MIGRATION.md` 等 |
| P2 预研 | 后端能力稳定后的前端任务 | `P2_LONG_TERM_TASKS.md`、`P2_*` |
| 历史记录 | 日期型或阶段型事实记录 | `2026-*`、`PHASE_*` |

## 2. 当前主线文档

当前前端主线为 **P1.1 深度交互与可观测性工作台**，重点包含：

1. Runtime Tab 化、Execution 按需加载与深链上下文；
2. Agent 调试上下文与 Published Version 关联；
3. Workflow 生命周期与真实 Execution 状态联动；
4. Runtime / Agent / Workflow 之间通过真实 ID 建立诊断上下文；
5. 只消费已经稳定的 Backend Contract，不提前实现尚未完成 Runtime Acceptance 的 2.10-I 能力。

当前 `frontend` 已基于远端 `main` 最新提交 `c0271fc1def0dfb713ebf5f38d75430100b4bf0b`，并包含前端 Runtime 深链上下文提交 `6577871376b460ac42509e836339d6ccf0135c4d`。

## 3. 文档维护规则

### 3.1 单一事实来源

- 工程规则：`FRONTEND_DEVELOPMENT_GUIDELINES.md`。
- 当前任务状态：`FRONTEND_TASK_EXECUTION_PLAN.md`。
- 长期路线：`FRONTEND_LONG_TERM_ROADMAP.md`。
- 阶段设计：对应 `P1_*` / `P2_*` / `PHASE_*` 文档。
- 测试执行规则：`FRONTEND_PHASED_TESTING_AND_EXECUTION_PLAN.md` 与项目级开发准则。
- 文本规则：`FRONTEND_UI_TEXT_GUIDELINES.md`。

同一规则不得在多个长期规范文档中分别维护不同版本。历史记录可以引用规则，但不应重新定义规则。

### 3.2 新增文档前检查

提交新文档前必须依次检查：

```text
现有 docs 搜索
    ↓
确认是否已有对应设计 / 规则 / 任务记录
    ↓
能更新旧文档 → 更新旧文档
不能复用 → 新建文档
    ↓
补充索引 / 引用关系
    ↓
与代码、测试、验收放入同一交付单元
```

### 3.3 命名规范

新增长期文档优先使用大写语义名称：

- `FRONTEND_*`：跨领域前端规范、计划或架构；
- `P1_*` / `P2_*`：阶段任务；
- `<DOMAIN>_*`：单领域实现说明；
- `*_REGRESSION.md`：回归问题与验证；
- `*_TEXT_*`：文本治理；
- `YYYY-MM-DD-*`：仅用于有明确日期事实的历史记录。

禁止使用无语义的 `note.md`、`temp.md`、`new-*.md` 等名称。

### 3.4 状态记录

任务状态只能使用：`待实施`、`进行中`、`阻塞`、`已完成`。测试结果必须注明实际执行日期和命令；未执行不得写“通过”。

### 3.5 文档与代码绑定

独立功能的设计、源码、测试和验收记录属于同一交付单元时，应一次性提交。文档更新不能代替代码实现，也不能通过连续文档提交制造虚假进度。

## 4. 历史文档整理策略

现有文档存在不同阶段、不同命名风格和部分主题交叉，这是历史开发证据，不直接删除。后续整理遵循：

1. 不删除仍具工程证据价值的历史记录；
2. 新规则只进入正式规范文件；
3. 新任务只更新任务台账和对应阶段文档；
4. 重复内容逐步收敛到单一事实来源；
5. 历史文档通过索引定位，不复制全文；
6. 只有在确认没有引用、没有独立验收价值且可以安全迁移时，才允许后续进行文件合并/删除，并必须作为独立原子文档整理提交。

## 5. 当前文档维护优先级

```text
FRONTEND_DEVELOPMENT_GUIDELINES.md
        ↓
FRONTEND_TASK_EXECUTION_PLAN.md
        ↓
P1_1_DEEP_OBSERVABILITY.md
        ↓
对应 Runtime / Agent / Workflow 功能文档
        ↓
测试与回归记录
        ↓
FRONTEND_LONG_TERM_ROADMAP.md
```

当前阶段优先更新主线文档和真实实现记录，不继续扩张重复的设计文档。
