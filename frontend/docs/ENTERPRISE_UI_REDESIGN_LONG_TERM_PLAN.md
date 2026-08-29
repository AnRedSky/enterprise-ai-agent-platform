# 前端企业级 UI 重构与长期优化计划

> 基线：`main` / `5a59d43d`。本轮以当前后端已经落地的 Agent、Tool、Knowledge、Workflow、Runtime、Organization、Model Provider、Usage、Webhook Integration 能力为边界，先建立统一企业工作台，再按领域逐页深化。

## 1. 本轮设计决策

### 1.1 信息架构
前端统一采用五层导航：工作台、AI 资产、自动化、运行与治理、平台管理。

- 工作台：总览，承担运营入口和异常发现。
- AI 资产：Agent、Tool、Knowledge，强调资产生命周期。
- 自动化：Workflow、Trigger，强调编排、发布和调度。
- 运行与治理：Runtime、Audit，强调 Execution、Event、Trace 与审计闭环。
- 平台管理：Organization、Integration，强调租户、成员、模型与外部系统连接。

该结构与后端领域边界对齐，避免以技术模块直接驱动 UI 信息架构。

### 1.2 Shell
统一 AppShell 增加工作区上下文、全局搜索入口、明确的领域分组、稳定的当前路由高亮和移动端降级。Shell 只负责导航、上下文和会话，不承载领域业务逻辑。

### 1.3 集成中心
Webhook Destination 与 Event Subscription 采用同一工作区，以指标卡 + 安全提示 + 双 Tab 组织。Secret 只显示“已配置/未配置”，禁止展示明文。状态展示使用语义化状态，不把后端字段直接暴露为技术细节。

### 1.4 权限边界
当前前端角色来自登录响应，仅用于导航和交互呈现；真正的 Tenant boundary、权限校验和资源授权仍由后端负责。后续增加页面级能力矩阵时不得复制后端授权算法。

## 2. 长期页面演进路线

### P0：统一基础体验
1. 完成 AppShell、登录、全局反馈、空状态、错误状态、加载状态统一。
2. 抽取页面 Header、Metric、Toolbar、DataTable、DetailPanel、ConfirmDialog 等基础模式。
3. 统一间距、字号、边框、状态色和响应式断点。

### P1：核心 AI 资产
1. Agent：列表 → 编辑 → 版本 → 发布 → Chat 调试形成完整生命周期。
2. Tool：能力目录、启停、风险提示、关联 Agent。
3. Knowledge：知识库列表、工作台、检索、文档状态与错误反馈。
4. Model Provider：Provider / Profile / Model 能力按组织上下文呈现。

### P2：自动化与运行闭环
1. Workflow：编排、草稿、发布、执行历史。
2. Trigger：Cron / Event / Webhook 等触发入口按状态管理。
3. Runtime：Execution 列表、详情、Event、Trace、失败定位。
4. Audit：按用户、资源、动作、时间和结果筛选，形成治理证据链。

### P3：企业管理与运营
1. Organization：组织、成员、角色和组织级模型配置。
2. Integration：Destination、Subscription、Delivery 状态和后续 Replay/诊断入口。
3. Usage：模型调用量、Token、成本、Provider/Model 维度分析。
4. Dashboard：从静态指标升级为可操作的运营驾驶舱，所有指标均来自真实 API。

### P4：平台级体验
1. 全局搜索与快捷命令。
2. 页面级权限和能力矩阵可视化。
3. 通知中心与运行异常聚合。
4. 可访问性、键盘操作、国际化、主题与大屏适配。
5. Playwright 关键用户旅程覆盖。

## 3. 页面统一契约

每个业务页面必须具备：

- 页面标题与业务目的；
- 主操作和次操作明确分层；
- Loading / Empty / Error / Success 四类状态；
- 列表查询条件与分页行为可追踪；
- 详情页能够回到领域列表；
- 破坏性操作必须确认并处理后端错误；
- Secret、Token 等敏感信息不在 UI 明文回显；
- 所有业务数据来自正式 API 类型，不创建第二套前端业务事实。

## 4. 测试策略

Frontend Unit/View：`frontend/tests/`，使用 Vitest 验证组件状态、交互和 API 调用边界。

Frontend Gate：`npm test` → `npm run build`，禁止依赖 Backend Gate。

Browser E2E：仅在真实 Frontend + 真实 Backend HTTP 链路上验证关键用户旅程，不替代单元测试。

本轮已修复 Integrations 页面 Vue 模板中 `el-tag` `:type` 表达式嵌套引号导致的编译错误，并保持现有 Integration 测试断言语义不变。

## 5. 验收基线

开发者本地执行并记录实际结果：

```powershell
cd frontend
npm test
npm run build
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

涉及真实后端数据时，再按项目治理规则独立执行 Backend Gate / Real API Gate；不得用前端 Mock 结果声称后端联调通过。

## 6. 原子提交规则

本轮 Shell + Integration UI + 对应测试/文档属于一个完整交付单元，采用单个原子提交。后续每个 UI 领域切片必须保持“代码、测试、设计记录”可追溯；测试反馈产生的新问题应形成新的、语义单一的修复提交。
