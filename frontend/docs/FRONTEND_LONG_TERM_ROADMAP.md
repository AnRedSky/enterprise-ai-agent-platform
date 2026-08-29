# Frontend 长期优化路线图

## 目标

将当前以“页面可用 + API CRUD”为主的前端逐步演进为企业级 AI Agent Control Plane：以租户边界、权限、Runtime、Workflow、Integration、Audit 和 Operations 为统一产品语言，并保持 UI 不复制 Backend 业务规则。

## F1：稳定性与设计系统

- 收口 Vitest 中所有未解析 Element Plus 组件警告。
- 建立统一页面壳、标题区、指标卡、Toolbar、Empty / Error / Loading 状态。
- 建立统一中文状态文案、时间格式、错误提示和危险操作确认规范。
- 为核心 View 建立 API Contract → Loading → Empty → Error → Success 测试矩阵。
- 保持 `npm run test:gate` 为 Frontend 独立质量门禁。

## F2：Runtime / Integration Operations

- Integrations 增加 Integration Event 查询入口，与 Backend tenant-scoped query contract 对齐。
- Delivery Operations 增加分页、状态统计、失败原因分组、Replay 前置条件展示。
- Runtime 页面统一展示 execution、tool、retrieval、model、scheduler 关键事实。
- Audit 与 Integration Event 建立业务事实到投递事实的导航关系，但不展示敏感 payload。

## F3：Workflow / Agent 工作台

- Workflow 升级为“设计 → 校验 → Trial → 发布 → 执行 → Trace”连续工作流。
- Agent 补齐模型、Tool、Knowledge、Runtime Policy 关联视图。
- Runtime 状态统一状态机视觉语言。
- 长任务提供可恢复 loading、polling、cancel UX。

## F4：企业治理

- IAM / Organization / Role / Permission 统一信息架构。
- 所有写操作显示 tenant scope、权限失败和审计结果。
- Secret 只显示引用与配置状态，不允许浏览器读取真实 Secret。
- 危险操作统一二次确认、影响范围摘要和操作结果。

## F5：Observability / SRE Console

- Runtime health、Scheduler、Worker、Webhook Delivery、Retry、Dead Letter 形成统一运维视图。
- 指标、事件、Audit、Trace 建立关联 ID 导航。
- 建立首屏、路由切换、列表刷新、长任务反馈性能预算。
- 高频列表采用分页、虚拟滚动或增量刷新，避免无限制加载全量数据。

## F6：生产化体验

- Playwright 覆盖登录、组织、Agent、Workflow、Integration、Runtime 主链路。
- 建立桌面端常用分辨率、窄屏和异常网络回归矩阵。
- 增加无障碍基础检查、键盘操作、焦点管理和表单错误可达性。
- 统一前端错误分类：Contract、Permission、Network、Validation、Runtime、Unknown。

## 长期约束

1. Backend Contract 是唯一业务契约；前端不得根据猜测扩展字段。
2. UI 只负责交互状态和展示，不复制 Runtime / Scheduler / Delivery 业务算法。
3. 新增 API 前先检查 `frontend/src/api` 是否已有正式入口。
4. 新增组件前先检查现有公共组件和页面模式，避免平行实现。
5. 每个新业务页面必须考虑 Loading、Empty、Error、Permission、Success 五种状态。
6. 复杂页面必须在 `frontend/docs` 记录信息架构、状态模型、API 依赖和边界。
7. 每个交付单元保持原子提交；代码、测试和对应设计文档具有同一交付意义时一次提交完成。
