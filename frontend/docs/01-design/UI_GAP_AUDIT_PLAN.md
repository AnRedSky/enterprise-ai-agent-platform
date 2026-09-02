# Frontend UI 完整性 Gap Audit 与 P0/P1 补齐计划

> 状态：执行中
> 基线：`frontend` 当前已同步最新 `main`
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
| P0 | Runtime | 已建立 | 核心已建立 | 持续补齐 | 核心链路已建立 | 进行中 |
| P0 | Workflow Lifecycle | 已建立 | 已建立 | 核心闭环已建立 | 已建立 | 基本完成 |
| P0 | Workflows | 待统一 | 部分已有 | 已有较多真实操作 | 待审计 | 进行中 |
| P0 | Agents | 基础模式已建立 | 已有 | 待完整审计 | Runtime 链路待强化 | 进行中 |
| P1 | Knowledge | 基础模式已建立 | 已有 | 待完整审计 | 待审计 | 进行中 |
| P1 | Tools | 基础模式已建立 | 已有 | 待完整审计 | 待审计 | 进行中 |
| P1 | Organizations | 待统一 | 待审计 | 待完整审计 | 待审计 | 待处理 |
| P1 | Model Providers | 待统一 | 待审计 | 待完整审计 | 待审计 | 待处理 |
| P1 | Integrations | 待统一 | 待审计 | 待完整审计 | 待审计 | 待处理 |
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
- Targeted tests → unit suite → build → gate。

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

## 7. 当前第一批实施项

**P0-01 Workflows 页面 UI-03/UI-04 收敛**：以现有真实 Workflow API 为边界，将页面结构逐步迁移到 `PageHeader` / `PageToolbar` / `SurfaceCard` / `StatePanel`，不改变既有业务 Contract；先完成页面骨架与列表状态，再处理 Detail/Execution 操作区。

**P0-02 Runtime 工作台**：在现有 Durable Fact 深链基础上审计 Execution / Trace / Audit 页面之间的 ID 传递和状态恢复。

**P0-03 Agent Debug**：审计 Agent Version、Debug、Runtime 三者的真实 ID 与操作 Contract。
