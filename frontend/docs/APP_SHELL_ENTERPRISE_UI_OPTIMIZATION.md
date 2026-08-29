# Frontend Enterprise Shell UI 优化

## 1. 本次交付

基于远端 `main` 当前基线，完成 AppShell 的一次企业级 UI 基础层优化。目标不是增加平行业务能力，而是先稳定所有业务页面共同依赖的导航、上下文和响应式容器。

后端当前处于 Phase 2.9 Enterprise Integration / Event Infrastructure，Webhook 已完成 Provider 第一切片；destination/subscription 持久化与可靠投递编排仍属于后端下一任务。因此本次前端不虚构尚未形成正式 API Contract 的 Webhook 管理页面，而是优先建设可承载后续 Integration Console 的稳定壳层。

## 2. 实现内容

### 2.1 导航状态

- 组织详情及模型 Provider 子页面统一归属于“组织管理”导航上下文。
- 工作流触发器保持 `/workflows/triggers` 精确激活，避免父级菜单状态丢失。
- 工作流相关路径自动展开父级菜单。
- 侧边栏折叠状态写入 `localStorage`，刷新页面后保持用户选择。

### 2.2 企业工作区视觉层

- 统一侧边栏、顶部 Header、内容区的边界与间距。
- 收敛导航项高度、圆角、激活态和 hover 态，降低视觉噪声。
- 品牌区改为语义化 button，支持键盘和辅助技术识别。
- 折叠按钮增加可访问名称。
- 页面切换增加轻量 transition，避免路由切换时内容突然跳变。

### 2.3 响应式策略

- 桌面端保留完整侧边栏和用户信息。
- 700px 以下自动进入窄侧栏模式。
- 移动窄屏隐藏不必要的 Header 辅助操作，保留核心身份与导航入口。
- 内容容器允许长表格和工作台页面独立滚动，避免全局布局被业务内容撑破。

## 3. 设计决策

1. **导航状态以路由为唯一事实来源**：不在 AppShell 维护第二份业务页面状态。
2. **不新增未由 Backend Contract 支撑的 Integration API**：Phase 2.9-D destination/subscription 尚未完成前，前端不创建假接口或假数据页面。
3. **持久化仅保存 UI 偏好**：折叠状态属于纯客户端偏好，不进入后端，也不携带 tenant 数据。
4. **不引入新的 UI 框架**：继续使用既有 Vue 3 + TypeScript + Element Plus，避免增加依赖和视觉系统分裂。

## 4. 测试设计

新增 AppShell 回归覆盖：

- 平台导航与用户上下文；
- Agent 导航路由跳转；
- 组织详情路径的导航高亮与标题；
- 侧边栏折叠状态持久化。

本次变更完成后应执行：

```powershell
cd frontend
npm install
npm test -- tests/views/AppShell.test.ts
npm test
npm run build
npm run test:gate
```

Browser 手动验证至少覆盖桌面宽度、窄屏宽度、组织详情、工作流触发器、折叠/刷新恢复和退出登录。

> 本次开发环境无法直接访问用户 Windows 工作目录，因此不会伪造本地执行结果；最终本地验收以开发者实际执行输出为准。
