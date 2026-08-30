# 前端分阶段测试与主线执行计划

> 基线：远端 `main`。本文件用于解决开发期间只能执行全局 `npm test`、日志过长且难以定位领域问题的问题。

## 1. 执行原则

当前阶段继续以**主线功能开发优先**为原则：

1. 先完成后端已经稳定提供的前端 API Contract、页面功能和 UI 闭环；
2. 主线任务全部完成前，不执行全量回归、生产构建和浏览器全链路验收；
3. 开发过程中只维护自动化测试脚本和测试实现，不以测试结果阻塞尚未完成的主线功能开发；
4. 每个领域使用独立 Vitest 入口，避免 `npm test` 产生全项目长日志；
5. 主线全部完成后，再按“领域 Gate → 全量 Frontend Gate → Browser E2E”顺序进入集中测试阶段。

## 2. 主线领域顺序

### P1 AI 资产
`Agent → Knowledge → Tool → Model Provider`

目标：形成 AI 资产管理、配置、版本与调试闭环。

### P2 自动化与运行
`Workflow → Trigger → Runtime`

目标：形成编排、发布、执行、失败定位与运行详情闭环。

### P3 企业治理
`Organization → Audit → Integration → Dashboard/Usage`

目标：形成租户、成员、治理、集成和运营闭环。

### P4 平台体验
`AppShell → 全局搜索 → 权限呈现 → 通知 → Accessibility/i18n/Theme → E2E`

## 3. 分阶段测试入口

### Phase P1：AI 资产

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-1-ai-assets.ps1
```

仅运行 Agent、Knowledge、Tool、Model Provider 相关测试。

### Phase P2：自动化与运行

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2-automation-runtime.ps1
```

仅运行 Workflow、Workflow Trigger、Runtime 相关测试。

### Phase P3：企业治理

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-3-governance.ps1
```

仅运行 Organization、Audit、Integration、Dashboard 相关测试。

### Phase P4：平台体验

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-4-platform-experience.ps1
```

仅运行 Shell、登录、共享组件和平台体验测试。

### 最终全量 Gate

只有 P1-P4 主线功能全部完成后执行：

```powershell
cd frontend
npm test
npm run build
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

## 4. 输出控制

阶段脚本使用 Vitest 的文件过滤能力，不通过 shell 重定向吞掉错误，也不修改测试实现。失败时保留失败测试名称和断言，便于直接定位领域问题。

脚本必须满足：

- 可重复执行；
- 不修改生产代码和测试代码；
- 不调用 Backend Gate、Real API Gate 或数据库迁移；
- 不把阶段测试结果伪装为全量回归结果；
- 退出码直接反映 Vitest 结果。

## 5. 完成定义

主线领域只有同时满足以下条件才能标记完成：

- 后端已有正式 Contract 已被前端 API 类型覆盖；
- 页面具备 Loading / Empty / Error / Success 状态；
- 主要 CRUD / 生命周期动作已连接正式 API；
- 技术状态值有统一用户态中文展示，并保留必要技术标识；
- 敏感信息不明文展示；
- 领域测试实现已经存在；
- 对应阶段测试脚本已经存在；
- 设计与实现记录已同步到 `frontend/docs`。

## 6. 最终验收阶段

主线开发完成后再集中进行：

1. P1-P4 分阶段测试；
2. Frontend 全量 Unit/View；
3. Production Build；
4. 真实 Backend HTTP 联调；
5. Playwright 关键用户旅程；
6. 响应式与可访问性检查；
7. 最终上线就绪评估。
