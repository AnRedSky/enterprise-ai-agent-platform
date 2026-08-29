# Frontend 长期优化路线图

## 当前基线

截至 2026-08-29，前端基于远端 `main` 最新基线 `a041a1f94030d9b347a777d467ad38d329de9016`。核心业务页面已经覆盖 Dashboard、Agent、Tool、Knowledge、Workflow、Trigger、Runtime、Audit、Organization、Model Provider、Integration 和 Runtime Operations；当前重点从页面覆盖转向企业级一致性、2.10-I 运维能力前端化和上线证据闭环。

完整评估见 `frontend/docs/FRONTEND_COMPREHENSIVE_ASSESSMENT_2026-08-29.md`。

## 目标

将当前以“页面可用 + API CRUD”为主的前端逐步演进为企业级 AI Agent Control Plane：以租户边界、权限、Runtime、Workflow、Integration、Audit 和 Operations 为统一产品语言，并保持 UI 不复制 Backend 业务规则。

## F0：稳定性与文本规范收口

- 清理所有用户可见的 `error.message`、HTTP 原文、英文状态枚举和后端错误码直出。
- 建立统一中文状态字典：已知状态显示通俗中文，未知状态显示“未知状态（技术值）”。
- 每个核心页面建立 Loading / Empty / Error / Success / Permission 回归矩阵。
- 保持 `npm test`、`npm run build`、`npm run test:gate` 为独立 Frontend Gate。

## F1：设计系统与基础体验

- 收口 Vitest 中所有未解析 Element Plus 组件警告。
- 建立统一页面壳、标题区、指标卡、Toolbar、Empty / Error / Loading 状态。
- 抽取 PageHeader、MetricCard、QueryToolbar、DataTable、DetailPanel、ConfirmDialog 等公共模式。
- 建立统一 Design Token：颜色、字号、间距、圆角、边框、阴影、断点。
- 建立统一中文状态文案、时间格式、错误提示和危险操作确认规范。
- 建立 1440 / 1280 / 1024 / 768 / 390 固定响应式验收矩阵。

## F2：Runtime / Integration Operations

- Integrations 保持 Integration Event、Delivery、Audit、Replay 闭环。
- Runtime Operations 增加 Provider Registry、Health、Alert、Notification Routing、Metric Series。
- Provider 支持能力、健康状态、fallback tier 和失败诊断展示。
- Alert 支持规则、阈值、窗口、firing/recovery 生命周期。
- Notification 支持 Destination 路由、Provider fallback、SLO、失败审计。
- Runtime / Integration 建立 Event → Delivery → Audit → Replay → Notification 关联导航。

## F3：Workflow / Agent 工作台

- Workflow 升级为“设计 → 校验 → Trial → 发布 → 执行 → Trace”连续工作流。
- Agent 补齐模型、Tool、Knowledge、Runtime Policy 关联视图。
- Runtime 状态统一状态机视觉语言。
- 长任务提供可恢复 loading、polling、cancel UX。
- Agent 调试结果与 Runtime Trace 建立一键关联。

## F4：企业治理

- IAM / Organization / Role / Permission 统一信息架构。
- 所有写操作显示 tenant scope、权限失败和审计结果。
- Secret 只显示引用与配置状态，不允许浏览器读取真实 Secret。
- 危险操作统一二次确认、影响范围摘要和操作结果。

## F5：Observability / SRE Console

- Runtime health、Scheduler、Worker、Webhook Delivery、Retry、Dead Letter、Alert 形成统一运维视图。
- 指标、事件、Audit、Trace 建立关联 ID 导航。
- 建立首屏、路由切换、列表刷新、长任务反馈性能预算。
- 高频列表采用分页、虚拟滚动或增量刷新，避免无限制加载全量数据。
- 接入 Prometheus / OpenTelemetry 展示与配置状态，但不在浏览器暴露 Secret。

## F6：生产化体验

- Playwright 覆盖登录、组织、Agent、Workflow、Integration、Runtime 主链路。
- 建立桌面端常用分辨率、窄屏和异常网络回归矩阵。
- 增加无障碍基础检查、键盘操作、焦点管理和表单错误可达性。
- 统一前端错误分类：Contract、Permission、Network、Validation、Runtime、Unknown。
- 建立前端版本与后端 Contract 的可追溯关系。

## F7：平台级体验

- 全局搜索与快捷命令。
- 页面级权限和能力矩阵可视化。
- 通知中心与运行异常聚合。
- Dashboard 趋势、可配置卡片和运营驾驶舱。
- 主题、大屏和国际化。

## 页面交付优先级

| 优先级 | 页面/领域 | 下一阶段重点 |
|---|---|---|
| P0 | Runtime Operations | 2.10-I Provider / Alert / Notification / Metrics |
| P0 | Integration | Notification → Delivery → Audit 闭环 |
| P0 | Model Provider | Registry / Health / fallback / SLO |
| P0 | Runtime | Execution → Event → Trace → Audit |
| P0 | Agent | 发布前校验、Trial、关联 Tool / Knowledge |
| P1 | Workflow | 编排 → 校验 → Trial → 发布 → Trace |
| P1 | Knowledge | 摄取、索引、检索质量与 Agent 关联 |
| P1 | Tool | Schema、风险、调用历史、Runtime 关联 |
| P1 | Organization | Role / Permission / Tenant 管理 |
| P1 | Audit | 多条件查询与跨领域证据链 |
| P1 | Dashboard | 运维趋势与异常聚合 |
| P2 | 平台级 | 搜索、通知中心、主题、大屏、国际化 |

## 页面统一契约

每个业务页面必须具备：

- 页面标题与业务目的；
- 主操作和次操作明确分层；
- Loading / Empty / Error / Success / Permission 五类状态；
- 列表查询条件与分页行为可追踪；
- 详情页能够回到领域列表；
- 破坏性操作必须确认并处理后端错误；
- Secret、Token 等敏感信息不在 UI 明文回显；
- 所有业务数据来自正式 API 类型，不创建第二套前端业务事实；
- 用户可见文本使用通俗中文，技术标识只在确有诊断价值的上下文中保留。

## 测试策略

Frontend Unit/View：`frontend/tests/`，使用 Vitest 验证组件状态、交互和 API 调用边界。

Frontend Gate：`npm test` → `npm run build` → `npm run test:gate`，禁止依赖 Backend Gate。

Browser E2E：仅在真实 Frontend + 真实 Backend HTTP 链路上验证关键用户旅程，不替代单元测试。

文本回归：对页面用户可见文本扫描，禁止直接渲染 `error.message`、HTTP 错误正文、英文枚举；未知技术值必须按照统一格式保留。

## 验收要求

开发者本地实际执行并记录结果：

```powershell
cd frontend
npm test
npm run build
npm run test:gate
```

涉及真实后端数据时，再按项目治理规则独立执行 Backend Gate / Real API Gate；不得用前端 Mock 结果声称后端联调通过。

## 原子提交规则

1. 继续直接基于 `main`，不创建功能分支。
2. 每个功能或修复只形成一个原子提交。
3. 代码、测试、设计记录属于同一交付单元时一次提交完成。
4. 测试反馈产生的新问题形成新的、语义单一的修复提交。
5. 不通过连续文档提交制造虚假的开发进度；只有实际事实变化才更新文档。
