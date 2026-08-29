# 前端企业级整体信息架构与 UI 重构基线

## 1. 目标

本次重构把现有前端从“按后端接口平铺页面”调整为企业 AI 平台的运营控制台信息架构，同时保持现有业务路由与后端 Contract 兼容。

核心用户域分为：

- **平台管理员**：组织、成员、模型 Provider、集成、审计、运行治理；
- **AI 业务管理员/开发者**：Agent、Tool、Knowledge、Workflow、Trigger；
- **业务使用者**：工作台、Agent 调试/使用、运行结果与个人可见资产。

当前后端已经具备组织、Agent、Tool、Knowledge、Workflow、Scheduler、Runtime、Audit，以及 Phase 2.9 Event/Webhook 能力，因此前端导航按照“工作台 → AI 资产 → 自动化 → 运行与治理 → 平台管理”组织，而不是创建尚无后端 Contract 的虚拟模块。

## 2. 信息架构

```text
企业 AI 平台
├── 工作台
│   └── 总览
├── AI 资产
│   ├── 智能体
│   ├── 工具
│   └── 知识库
├── 自动化
│   ├── 工作流
│   └── 触发器
├── 运行与治理
│   ├── 运行中心
│   └── 审计日志
└── 平台管理
    ├── 组织与成员
    └── 集成中心
        ├── Destination
        └── Subscription
```

## 3. 本次实现

### AppShell

- 导航改为业务域分组；
- “运行记录”升级为“运行中心”；
- “组织管理”升级为“组织与成员”；
- 增加后端已实现 Contract 对应的“集成中心”；
- 用户菜单提供组织与集成入口；
- 保留组织详情、Workflow Trigger、Sidebar 持久化等既有行为；
- 不创建独立的管理员/普通用户两套 Shell，而通过同一 Shell + 权限感知导航演进，避免 UI 与权限逻辑分裂。

### 集成中心

直接绑定后端 `/webhooks/destinations` 与 `/webhooks/subscriptions`：

- Destination 列表；
- Destination 创建；
- Secret 只接受引用，不允许在 UI 输入明文 Secret；
- 自定义 Headers；
- Subscription 列表；
- Subscription 创建；
- Event Type / Priority；
- 空状态与错误反馈。

本页面不提前实现后端尚未提供的删除、编辑、Replay、Delivery 明细等操作，待对应 Contract 落地后再扩展。

## 4. 长期页面体系

### 业务端

- 企业工作台：跨 Agent / Workflow / Runtime 的业务入口；
- Agent 使用台：面向业务用户的 Chat/任务入口；
- 运行结果：业务可见的执行结果与状态。

### AI 开发端

- Agent Studio：定义、版本、模型、Tool、Knowledge、发布、调试；
- Tool Center：工具定义、启停与可用性；
- Knowledge Workbench：知识资产、索引、检索；
- Workflow Studio：编排、变量、条件、重试、发布、Trigger。

### 管理端

- Organization Center：组织、成员、角色、权限；
- Model Provider Center：Provider Profile 与模型能力；
- Integration Center：Destination、Subscription、Delivery；
- Runtime Operations：执行、事件、Trace、失败处理；
- Audit Center：治理审计与操作追踪。

### 平台运维端

随着 LT-03/LT-05/LT-06 落地，再增加 Operations、Observability、Security/Policy，而不是提前伪造数据页面。

## 5. UI 原则

1. 后端 Contract 优先：没有稳定 API 就不创建假数据功能；
2. 同一领域只保留一个正式入口；
3. 页面以“列表 + 状态 + 操作 + 详情”作为企业 CRUD 基础模式；
4. Runtime、Audit、Integration 使用状态驱动视觉，不以装饰性图表替代真实状态；
5. Secret、Token、Provider 凭据只显示引用/脱敏状态；
6. 所有页面必须具备 loading、empty、error、success 状态；
7. 桌面优先，同时保持 700px 以下可用；
8. 权限采用能力感知导航，后续与 Backend IAM Contract 对接后再细化菜单与操作级权限。

## 6. 后续重构顺序

```text
F1 Design System / Shell
        ↓
F2 Agent Studio
        ↓
F3 Workflow Studio
        ↓
F4 Runtime Operations
        ↓
F5 Integration Center
        ↓
F6 Organization / IAM
        ↓
F7 Observability / SRE
        ↓
F8 Enterprise Operations
```

每一阶段均遵循：

```text
Backend Contract
→ Frontend Type
→ API Test
→ View / Component
→ Vitest
→ Frontend Gate
→ Real API / Browser E2E（范围需要时）
→ frontend/docs 记录
```

## 7. 验证

固定 Frontend Gate：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

本次提交增加：

- `tests/api/integrations.test.ts`
- `tests/views/Integrations.test.ts`

本地测试结果必须以开发者实际执行结果为准，不在文档中预填通过结论。
