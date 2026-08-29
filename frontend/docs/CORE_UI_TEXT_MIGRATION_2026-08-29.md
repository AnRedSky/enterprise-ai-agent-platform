# 核心页面 UI 文本中文化记录（2026-08-29）

## 1. 本次范围

本次继续按照 `FRONTEND_UI_TEXT_GUIDELINES.md` 扫描并修正以下已有页面：

- 组织列表
- 组织详情
- 模型提供方与模型配置
- 审计日志
- Dashboard

Runtime 与 Workflow 页面同步完成扫描；现有用户可见文本已经基本符合中文规范，保留的英文主要属于技术标识、枚举值或字段标识，因此本轮不修改业务逻辑。

## 2. 修改原则

1. 只修改已有页面中的用户可见文本，不复刻或新建中文版 UI。
2. 保持现有布局、组件、样式、路由、API 调用和业务流程不变。
3. 后端枚举、API 参数、资源 ID、User ID、Tenant ID、Dimension、错误码及其他技术标识保持原值。
4. 后端状态值通过前端显示映射转换为通俗中文，不改变实际提交值。
5. 每个页面增加中文文案回归测试，防止后续修改重新引入英文 UI 文案。

## 3. 页面落地

### 组织列表

- `Organizations` → `组织`
- `创建 Organization` → `创建组织`
- `Organization 创建成功` → `组织创建成功`
- `Organization 列表加载失败` → `组织列表加载失败`
- `active` 显示为 `已启用`
- `Tenant ID` 保留，作为技术字段标识

### 组织详情

- `Organizations` → `返回组织列表`
- `Organization` → `组织`
- `Model Provider / Profile` → `模型提供方 / 模型配置`
- `Admin / Member / Owner` → `管理员 / 成员 / 所有者`
- `active / suspended` 显示为 `已启用 / 已暂停`
- `User ID` 保留，作为技术字段标识
- 所有权转移、成员状态变更等 API 参数保持原值

### 模型提供方与模型配置

- 页面标题、创建、编辑、删除、保存及错误提示统一使用中文
- `Provider` 在普通用户可见文案中统一表达为“模型提供方”
- `Profile` 在普通用户可见文案中统一表达为“模型配置”
- `enabled / disabled` 显示为 `已启用 / 已停用`
- `chat / embedding` 在选择项中分别显示为“对话模型 / 向量模型”，提交值保持不变
- `Dimension` 保留，作为模型技术参数名称

### 审计日志

- `Audit Logs` → `审计日志`
- `Status` → `状态`
- `Action` → `操作`
- `Agent` → `智能体`
- `Tool` → `工具`
- `Created At` → `创建时间`
- 错误提示统一为“审计日志查询失败”
- 审计 action/status 实际值保持后端原值，便于排障

### Dashboard

- `ENTERPRISE AI AGENT PLATFORM` → `企业级智能体平台`
- Agent → 智能体
- Tool → 工具
- Runtime → 运行记录
- Published → 已发布
- 快捷入口、指标卡、失败提示和最近执行区域统一使用中文
- 快捷入口图标中的英文缩写改为简短中文标识，不改变导航路径

## 4. 测试覆盖

对应页面测试增加中文文案断言，并同时验证技术标识仍然保留：

- `frontend/tests/views/Organizations.test.ts`
- `frontend/tests/views/OrganizationDetail.test.ts`
- `frontend/tests/views/ModelProviders.test.ts`
- `frontend/tests/views/AuditLog.test.ts`
- `frontend/tests/views/Dashboard.test.ts`

回归测试重点检查：

- 页面核心标题为中文
- 按钮和操作文案为中文
- 状态显示为中文
- 不再出现已扫描到的英文业务文案
- Tenant ID、User ID、Dimension、资源 ID 等技术标识不被误翻译
- API Contract 和后端枚举提交值保持不变

## 5. Runtime / Workflow 扫描结论

### Runtime

现有 `RuntimeExecutions.vue` 的页面标题、查询、错误、空状态、运行时间线、工作流运行链路等已经使用中文。`Top K`、ID、节点 ID、错误代码、事件类型和后端状态原值属于技术信息，不作为普通业务文案翻译。

### Workflow

现有工作流页面已经使用中文状态映射、操作提示、确认框和错误提示。JSON、ID、节点 ID、版本 ID 等属于技术内容，继续保持原值。当前不进行无必要的 UI 重构。

## 6. 后续策略

继续按“扫描 → 中文化 → 技术标识保留 → 文案回归测试 → 构建验证”的顺序处理新增或遗漏页面。禁止通过复制页面、增加第二套组件或引入独立中文版 UI 的方式解决文本问题。
