# Frontend UI 完整性 Gap Audit 与 P0/P1 补齐计划

> 状态：执行中  
> 基线：`frontend` 当前已同步最新 `main` 目标：建立可持续更新的全站 UI 完整性基线，并作为当前前端任务执行台账。  
> 原则：真实 Backend Contract、公共 UI 模式、逐页补齐、targeted test、文档同步、原子提交。

## 1. 目标

建立一份可持续更新的全站 UI 完整性基线，逐页检查并补齐：

- UI-03：PageHeader / PageToolbar / SurfaceCard / MetricCard 等公共页面模式
- UI-04：Loading / Empty / Error / Permission / Success 状态
- UI-05：Form / Dialog / Drawer / Confirm / Action / Refresh 闭环
- Durable Fact / ID 驱动的跨页面深链
- Backend API Contract 与错误处理
- Permission 与不可操作状态
- Targeted unit test / build / gate

## 2. 审计维度

每个页面按以下 8 项检查：

1. 页面结构：是否使用统一 Header / Toolbar / SurfaceCard。
2. 数据状态：Loading / Empty / Error / Permission / Success 是否完整。
3. 操作闭环：Create / Edit / Delete / Execute / Retry / Publish 等是否有真实 API Contract。
4. 操作安全：Confirm、取消、重复提交、失败恢复、刷新是否正确。
5. 数据事实：不得通过时间、数组顺序、字符串或分页位置推断实体关系。
6. 深链：URL 是否携带真实 durable ID，反向导航是否恢复准确上下文。
7. 权限：403 是否统一展示 Permission 状态，并禁用不允许的操作。
8. 测试：关键路径是否有 targeted Vitest，构建与 gate 是否可验证。

## 3. 页面台账

| 优先级 | 页面 | UI-03 | UI-04 | UI-05 | 深链/诊断 | 状态 |
|---|---|---|---|---|---|---|
| P0 | Runtime | 已建立 | 核心已建立 | 持续补齐 | P0-02-A 已审计并补回归 | 待验证 |
| P0 | Workflow Lifecycle | 已建立 | 已建立 | 核心闭环已建立 | 已建立 | 基本完成 |
| P0 | Workflows | 已建立 | P0-01-B 已补齐 | P0-01-B 已补齐 | durable ID 保持 | 待验证 |
| P0 | Agents | 基础模式已建立 | Debug 已收敛 | P0-03-A 已补齐关键防护 | Runtime 链路待强化 | 待验证 |
| P1 | Knowledge | 已建立 | 已有 | 第一轮审计完成 | durable ID 层级保持 | 待验证 |
| P1 | Tools | 已建立 | 已有 | 第一轮审计完成 | durable ID 保持 | 待验证 |
| P1 | Organizations | 待统一 | 待审计 | 待完整审计 | 待审计 | 待处理 |
| P1 | Model Providers | 待统一 | 待审计 | 待完整审计 | 待审计 | 待处理 |
| P1 | Integrations | 待统一 | 待审计 | 待完整审计 | Runtime 关联待审计 | 待处理 |
| P1 | Operations Console | 待统一 | 待审计 | 待完整审计 | Runtime 关联待审计 | 待处理 |
| P1 | Audit | 基础模式已建立 | 待全站收敛 | 读操作为主 | 与 Runtime 关联 | 待处理 |
| P1 | Dashboard | 已建立 | 已建立 | 以导航为主 | 待审计 | 收尾 |

## 4. 执行顺序

### Phase A：基线同步与审计

- 同步 `main` → `frontend`。
- 固化本计划。
- 对全部业务路由进行 UI-03/UI-04/UI-05 Gap Audit。
- 每次审计只记录可由代码、API Contract、测试证明的事实。

### Phase B：P0 页面补齐

1. Runtime：继续强化 Execution → Trace → Audit → Workflow/Agent 的诊断工作台。
2. Workflow Lifecycle：保持为 UI-05 canonical reference，只补发现的缺口。
3. Workflows：将现有业务操作迁移到统一页面模式，并补齐状态/权限/操作闭环。
4. Agents：以 Agent → Version → Debug → Runtime 为主线补齐。

### Phase C：P1 页面补齐

依次处理：Knowledge → Tools → Organizations → Model Providers → Integrations → Operations → Audit。

### Phase D：全站一致性回归

- Responsive / spacing / typography / status semantics。
- Permission / unknown status / error message。
- Deep-link / refresh / browser back-forward。
- 所有阶段测试脚本准备完成后，再统一执行 targeted tests → unit suite → build → gate。

## 5. 业务操作 Contract 原则

- 前端只能调用已存在并确认的 Backend API。
- Scheduler 写操作在完整 HTTP Contract、状态机、lease、misfire、audit/trace 关联确认前保持只读。
- Webhook secret 不回显、不读取旧 secret、不在未修改时重新提交。
- 成功后的 UI 状态必须以 Backend refresh 为准，不本地伪造持久状态。

## 6. Definition of Done

页面只有同时满足以下条件才从“进行中”变为“完成”：

- [ ] UI-03 公共页面模式完成
- [ ] UI-04 五态完整
- [ ] UI-05 关键操作闭环完成
- [ ] Backend Contract 已确认
- [ ] 无前端关系推断
- [ ] 深链使用 durable ID
- [ ] 关键路径 targeted test 通过
- [ ] `npm run test:unit` 通过
- [ ] `npm run build` 通过
- [ ] 文档同步
- [ ] 原子提交

**测试策略：** 在全部页面开发、targeted 测试脚本和文档阶段完成之前，禁止执行测试；测试脚本可以先分阶段补齐并保持“未执行”状态。全部任务完成后再按 targeted → unit → build → gate 顺序统一验证。

## 7. 当前实施进度

### P0-01-A Workflows UI-03

代码实现已完成：`workflows/index.vue` 使用 `PageHeader`、`SurfaceCard`、`StatePanel` 统一页面骨架，并保留现有 Workflow CRUD、Version、Publish、Execution、Retry、Resume、Cancel、Trace、Audit API 与 durable ID 关系。

Targeted test：`frontend/tests/views/WorkflowsUI03.test.ts`。

当前测试状态：**未执行**。因此 P0-01-A 不标记“已完成”。

### P0-01-B Workflows UI-04/05

已完成第一轮补齐：Version Loading/Empty/Error/Permission、Execution/Audit stale-data 清理、Trace Loading 与重复查询保护、Create/Edit/Delete/Create Version/Publish action loading 与并发保护、Archived read-only 与确认框保护。

Targeted regression：`frontend/tests/views/WorkflowsUI04UI05.test.ts`。

当前测试状态：**未执行**。

### P0-02-A Runtime Execution / Correlation 深链状态恢复

代码审计确认 `RuntimeExecutions.vue` 使用真实 `execution_id` 恢复深链；当目标 Execution 不在当前分页列表中时直接 `openById(execution_id)`，不通过列表位置推断。关系导航使用后端 `workflow_id` 与目标 Execution ID，并固定携带 `source=runtime-relation`。

Targeted regression：`frontend/tests/views/RuntimeDeepLinkRecovery.test.ts`。

当前测试状态：**未执行**。

### P0-03-A Agent Workbench UI-05

已移除通过 `listVersions(agent.id)[0]` 推断“最新版本”的入口；发布必须基于明确 `version.id`。Archive、Create、Create Version、Publish 增加操作期间保护，成功后从 Backend refresh。

Targeted regression：`frontend/tests/views/AgentWorkbenchUI05.test.ts`。

当前测试状态：**未执行**。

### P0-04 Agent Debug

`AgentDebugExperience` 已迁移到 `SurfaceCard` + `StatePanel`，统一 Loading / Empty / Error 状态，并继续使用真实 Agent / Published Version API。`AgentDebugExperienceUI04.test.ts` 已建立，覆盖 Loading、Empty、Error。

### P1-01-A Knowledge

代码审计确认 Knowledge Workbench 已使用 `PageHeader`、`PageToolbar`、`SurfaceCard`、`StatePanel`，知识库 → 文档 → 版本 → 分块关系全部通过真实 ID 驱动；检索调用使用已确认 `/knowledge/retrieve` Contract，并保留 Backend 返回的 `document_id`、`document_version_id`、`chunk_id`、citation、retrieval source 等 durable facts。

本阶段新增 targeted regression：`frontend/tests/views/KnowledgeWorkbenchUI03UI05.test.ts`，覆盖：

- 公共页面 Header / Toolbar / SurfaceCard；
- Knowledge Base 403 Permission；
- Knowledge Base → Document → Version → Chunk 的真实 ID 调用；
- Hybrid retrieval Contract 与 Backend result facts。

当前测试状态：**未执行**。

### P1-02-A Tools

代码审计确认 Tools Workbench 已使用 `PageHeader`、`PageToolbar`、`SurfaceCard`、`StatePanel`、`ConfirmDialog`；工具启停、绑定/解绑、执行均使用明确 tool/agent ID 和已确认 API。危险状态变更有确认闭环，成功后刷新列表。

本阶段新增 targeted regression：`frontend/tests/views/ToolWorkbenchUI03UI05.test.ts`，覆盖：

- Loading / Error shared state；
- tool ID + agent ID 驱动执行；
- Enable/Disable confirmation；
- 成功后 Backend refresh。

当前测试状态：**未执行**。

### P1-03-A Organizations

已完成第一轮代码审计。当前组织列表仍使用自定义 Header / Alert / Empty；组织详情仍使用 `el-card`。下一原子任务为迁移列表与详情到公共 `PageHeader` / `SurfaceCard` / `StatePanel`，并补充成员权限、组织状态、所有权转移的 UI-05 targeted test。Backend Contract 已存在于 `frontend/src/api/organizations.ts`，不新增推测 API。

## 8. 下一批原子任务

1. P0-03-B：Agent Debug → Runtime durable ID 回归测试脚本。
2. P1-03-A：Organizations 列表 UI-03/UI-04/UI-05 迁移。
3. P1-03-B：Organizations detail UI-03/UI-04/UI-05 与成员权限闭环。
4. P1-04-A：Model Providers Gap Audit + targeted test 脚本。
5. P1-05-A：Integrations Gap Audit + targeted test 脚本。
6. P1-06-A：Operations Console Contract / Governance 对齐 + targeted test 脚本。
7. P1-07-A：Audit Gap Audit + Runtime correlation regression。
8. P1-08-A：Dashboard 与全站一致性回归脚本。
9. 全部开发完成后统一执行所有 targeted tests、unit、build、gate。

## 9. 任务执行跟踪规范

### 9.1 状态定义

| 状态 | 使用条件 |
|---|---|
| 待处理 | 已进入路线图，尚未开始审计/实现 |
| 审计中 | 正在核对页面、Contract、权限、状态或测试缺口 |
| 开发中 | 已确定最小实现范围并正在修改代码 |
| 待验证 | 代码已修改，但 targeted/full test/build/gate 尚未全部执行 |
| 阻塞 | 有明确 Backend Contract、环境、权限或其他阻塞原因 |
| 回归中 | 单页已完成，正在做跨页面一致性回归 |
| 已完成 | Definition of Done 全部满足且有实际验证记录 |

禁止使用“基本完成”“应该没问题”“已验证但未执行”等不可验收状态。

### 9.2 原子任务记录格式

```text
### <Task ID> <日期>
- 页面/模块：
- Gap：
- Contract：
- 实现范围：
- Targeted test：
- Targeted result：未执行
- Full unit：未执行
- Build：未执行
- Gate：未执行
- Real API / E2E：未执行
- 已知限制/阻塞：
- Commit：
- 下一任务：
```

### 9.3 执行顺序

```text
同步 main
  ↓
确认 Backend Contract
  ↓
页面 Gap Audit
  ↓
最小代码修改
  ↓
准备 targeted test（不执行）
  ↓
文档同步
  ↓
原子提交
  ↓
下一原子任务
  ↓
全部任务完成
  ↓
统一测试 targeted → unit → build → gate
```

### 9.4 当前执行队列

| 顺序 | Task ID | 交付目标 | 状态 |
|---|---|---|---|
| 1 | P0-01-A | Workflows 页面公共 Header / SurfaceCard / 列表状态 | 待验证 |
| 2 | P0-01-B | Workflows UI-04 / UI-05 targeted regression | 待验证 |
| 3 | P0-02-A | Runtime Execution / Correlation 深链状态恢复审计 | 待验证 |
| 4 | P0-03-A | Agent Workbench UI-05 操作闭环 | 待验证 |
| 5 | P0-03-B | Agent Debug → Runtime durable ID 回归 | 待处理 |
| 6 | P1-01-A | Knowledge 页面 Gap Audit + targeted test | 待验证 |
| 7 | P1-02-A | Tools 页面 Gap Audit + targeted test | 待验证 |
| 8 | P1-03-A | Organizations 页面 UI-03/UI-04/UI-05 | 待处理 |
| 9 | P1-03-B | Organizations detail 成员权限闭环 | 待处理 |
| 10 | P1-04-A | Model Providers 页面 Gap Audit | 待处理 |
| 11 | P1-05-A | Integrations 页面 Gap Audit | 待处理 |
| 12 | P1-06-A | Operations Console Contract / Governance 对齐 | 待处理 |
| 13 | P1-07-A | Audit 页面 Gap Audit | 待处理 |
| 14 | P1-08-A | Dashboard 与全站一致性回归 | 收尾 |

### 9.5 当前任务选择原则

继续遵循：

> **一个核心页面 → 公共模式迁移 → targeted test（先写不跑）→ 文档同步 → 原子提交 → 下一页面**

若当前任务发现 Backend Contract 不完整，应标记“阻塞”，先回到 Contract/Backend 验证，不得用 Mock 或猜测继续固化前端行为。