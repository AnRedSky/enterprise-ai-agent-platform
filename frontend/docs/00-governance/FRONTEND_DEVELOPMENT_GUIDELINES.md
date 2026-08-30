# 前端开发准则

> 本文件是 `frontend` 专用工程开发准则。项目级工程规则以 `docs/01-governance/DEVELOPMENT.md` 为最高约束；本文件只补充前端实现、验证、UI、文档和提交方面的具体执行规则。
>
> **规则优先级**：项目级开发准则 > 本文件 > 阶段/功能文档 > 临时讨论。若发现冲突，必须先修正文档，再继续开发。

## 1. 开发基线

- 每轮开发开始前必须同步远端 `main`，确认 Backend Contract、测试和验收状态。
- 当前项目禁止创建功能分支、临时分支、长期开发分支；前端变更直接基于并提交 `main`。若仓库当前存在历史 `frontend` 分支，只视为既有历史状态，不作为新开发分支规范。
- 后端稳定能力是前端正式实现的唯一前置条件；不得根据猜测、Mock 或未来设计提前固化业务 Contract。
- 开发顺序固定为：Backend Domain / Contract → Backend Tests / Acceptance → Frontend API Types → View / Component → Vitest → Real API / E2E。

## 2. 前端职责边界

前端负责展示、交互、表单校验、页面状态、用户操作编排和诊断上下文组织；后端负责业务规则、权限、tenant boundary、状态机、幂等、重试、事务、可靠投递和最终业务事实。

强制要求：

1. API 类型必须与正式 Backend Contract 对齐。
2. 不复制后端业务计算、状态机或权限规则作为第二套事实来源。
3. 状态展示只能基于后端真实值和明确映射。
4. Runtime / Agent / Workflow 等跨页面上下文必须通过真实资源 ID 建立关联，不通过页面猜测或本地拼接推断业务关系。
5. Contract 变化时先更新 API Types 和测试，再调整 UI。

## 3. UI 信息架构

- 优先保持现有企业级信息架构，采用渐进增强，不因局部视觉优化复制整套页面。
- 页面优先形成“概览 → 列表 → 详情 → 诊断/操作”的稳定路径。
- Runtime 等高信息密度页面优先使用 Tab、分层详情和按需加载，避免首次打开同时请求所有重型数据。
- 深链必须能够恢复必要上下文，例如 `execution_id`、`workflow_id`、`agent_id`、`source` 等真实技术标识。
- 危险操作必须明确业务影响，并在执行前确认。

## 4. 页面状态完整性

所有业务页面必须明确处理：

- Loading：请求期间给出稳定反馈；
- Empty：说明为什么为空及下一步；
- Error：提供用户可理解的原因和恢复动作；
- Success：明确反馈操作结果并刷新受影响状态；
- Permission：无权限时不可误导用户继续操作。

列表页还必须处理分页、刷新、筛选条件保持、请求竞态和失败恢复。

## 5. UI 文本与错误边界

- 用户可见文本统一使用通俗、准确的中文。
- 技术标识如 ID、Trace ID、事件类型、错误码可以保留，但必须放在诊断需要的位置并提供中文说明。
- 状态枚举统一映射；未知值显示 `未知状态（技术值）`，不得静默伪装成已知状态。
- 禁止直接展示 `error.message`、HTTP 错误正文、异常堆栈或 Provider 原始错误。
- 错误提示采用“发生了什么 + 下一步怎么办”。
- 按钮优先使用用户动作，例如“保存”“查看详情”“重新执行”，避免使用接口名或代码术语。
- 详细文本规则统一参照 `FRONTEND_UI_TEXT_GUIDELINES.md`，不要在业务文档中复制整套文本规范。

## 6. API、状态与数据加载

- API client 是唯一 HTTP 访问边界，View 不直接拼接受保护 Endpoint。
- 页面只请求当前用户操作真正需要的数据；详情、Trace、Audit 等重型数据优先按需加载。
- 同一资源在多个页面展示时，优先复用已有 API 类型、mapper 和公共组件。
- 不新增平行 API client、重复 mapper 或第二套状态枚举。
- 请求失败、取消、竞态和组件卸载必须不会污染后续页面状态。

## 7. Runtime / Agent / Workflow 特殊规则

### Runtime

- Execution、Event、Trace、Audit、Workflow 关系必须保持可追溯上下文。
- Runtime 默认加载轻量健康概览；用户进入 Execution / 诊断后再加载对应详情。
- `execution_id` 是 Execution 诊断的核心上下文，不得从 UI 文本猜测。

### Agent

- 调试上下文优先读取真实 Agent 与 Published Version。
- Version、Model、System Prompt 等信息必须来自正式 API Contract。
- Runtime 调试入口携带真实 `agent_id`，不得复制 Agent 状态到 Runtime 页面。

### Workflow

- 生命周期展示以 `Workflow` / `WorkflowExecution` 后端真实状态为准。
- Retry / Resume / Cancel / Run 只调用已有正式生命周期接口。
- 前端不得新增并行状态机或通过定时器模拟后端生命周期。

## 8. 公共组件与设计一致性

重复出现的模式必须优先复用：PageHeader、Toolbar、MetricCard、DataTable、DetailPanel、StatusTag、EmptyState、ErrorState、ConfirmDialog 等。

公共组件应保持：

- 单一职责；
- 明确 Props / Emits；
- 不包含领域业务规则；
- 可独立测试；
- 不通过隐式全局状态改变调用方行为。

局部页面不得为了视觉效果破坏全局间距、信息层级、响应式和交互语义。

## 9. 安全与多租户

- Secret、Token、API Key 等敏感信息不得进入 UI、日志或测试快照。
- 前端不得绕过后端权限直接访问受保护资源。
- tenant-scoped 数据必须以服务端返回事实为准，不得通过 query 参数、缓存或本地状态扩大数据范围。
- Replay、Retry、Delete、Archive 等高风险操作必须确认，并在权限不足时保持不可操作状态。

## 10. 测试规范

测试实现只放 `frontend/tests/`；测试脚本只放 `frontend/scripts/test/`。不得在业务源码中嵌入验收脚本。

### 标准顺序

```text
npm test -- <targeted-test>
        ↓
npm test
        ↓
npm run build
        ↓
npm run test:gate
        ↓
必要时 Real API / Browser E2E
```

当前本地依赖未安装时，不得用 `npx` 临时下载测试框架冒充项目测试环境。应先执行项目既定依赖安装流程，再使用 `package.json` 中的正式脚本；例如 Vitest 配置依赖 `vitest`、`@vitejs/plugin-vue` 时，必须保证它们存在于项目依赖中。

每个新增/修改业务页面至少覆盖：正常数据、Loading、Empty、Error、Permission、已知/未知状态、关键按钮、关键 API 参数和成功后状态刷新。

没有实际执行的测试不得记录为“通过”。GitHub Actions 不作为本地开发验收依据。

## 11. 文档规范

`frontend/docs` 按以下职责维护：

```text
规范      → FRONTEND_DEVELOPMENT_GUIDELINES.md
索引      → FRONTEND_DOCS_INDEX.md
任务台账  → FRONTEND_TASK_EXECUTION_PLAN.md
路线图    → FRONTEND_LONG_TERM_ROADMAP.md
测试计划  → FRONTEND_PHASED_TESTING_AND_EXECUTION_PLAN.md
阶段设计  → P1_* / P2_* / PHASE_*
领域设计  → <DOMAIN>_*
回归记录  → *_REGRESSION.md / *_REMEDIATION.md
文本治理  → FRONTEND_UI_TEXT_GUIDELINES.md / *_TEXT_*
```

新建文档前必须先搜索 `frontend/docs`，能更新既有文档就不得新建重复文档。历史文档不因命名不一致直接删除；应通过索引和单一事实来源逐步收敛。

文档必须记录实际事实：设计决策、Contract 对齐、实现范围、测试命令与实际结果、已知限制和下一任务。文档不能代替代码实现。

## 12. 原子提交

一个提交只包含一个具有独立工程意义的交付单元：

- 一个功能：源码 + 测试 + 必要设计/验收记录；或
- 一个修复：修复代码 + 回归测试 + 必要错误记录；或
- 一个独立文档治理任务：相关规范、索引和台账一次性完成。

禁止：

- 为同一任务连续创建多个文档中间提交；
- 先提交半成品再补测试制造“完成”记录；
- 将无关功能、格式化或重构混入当前提交；
- 通过拆分提交规避原子性要求。

提交信息采用 Conventional Commits，并准确描述单一交付目的。

## 13. 完成定义

只有同时满足以下条件才能标记任务“已完成”：

1. Backend Contract 已确认稳定；
2. API Types 与 Contract 一致；
3. 用户操作链路完整；
4. Loading / Empty / Error / Success / Permission 完整；
5. 中文 UI 文本和错误边界符合规范；
6. 安全与 tenant boundary 无明显绕过；
7. targeted Vitest 通过；
8. 全量 `npm test` 通过；
9. `npm run build` 通过；
10. `npm run test:gate` 通过；
11. 需要真实后端时完成对应联调/E2E；
12. `frontend/docs` 已同步实际实现与验收事实；
13. 提交是语义单一的原子提交。

若其中任一项尚未完成，状态应保持 `进行中` 或 `阻塞`，并明确阻塞原因。

## 14. 当前主线

当前重点为 **P1.1 深度交互与可观测性工作台**：Runtime Tab/按需加载、Agent 调试上下文、Workflow 生命周期与真实 Execution 联动。P1.1 之后继续完成核心业务闭环，再进入后端 2.10-I 稳定后的 Provider / Health / Alert / Notification / Metrics 前端化。
