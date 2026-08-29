# Dashboard UI 优化与回归修复

## 1. 基线

- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 基线提交：`93dc6af6`
- Backend 当前阶段：Phase 2.9-D Webhook Integration 第一实现切片已完成，下一步为 destination/subscription 持久化与可靠投递编排。
- 本次前端不提前实现 Webhook destination UI，因为后端持久化 Contract 尚未完成；Dashboard 继续只消费已经稳定的 Agent、Tool、Runtime API。

## 2. 本地反馈根因

最新开发者本地回归中，Dashboard 单测出现：

```text
Expected: / wrapper text contains 2
Received: Agent 0 ... Tool 0/0 ... Runtime 0 ...
```

Runtime mock 能被调用，但 Agent / Tool mock 与组件实际使用的 `@/api/*` 模块标识不完全一致，导致测试没有可靠隔离到组件依赖。生产组件本身仍使用正式 API 入口。

本次将测试 mock 统一到组件实际使用的 `@/api/agents`、`@/api/tools`，并给核心指标增加稳定 `data-testid`，避免用整页文本中的任意数字作为断言目标。

## 3. UI 优化

### 3.1 指标卡

保留现有五项核心指标，并增加稳定测试标识；不改变指标计算来源。

### 3.2 Runtime 活动摘要

在最近 8 条执行记录上方增加窗口级摘要：窗口记录、失败、进行中。该摘要只基于已经拉取的 Runtime 分页结果，不新增后端接口或复制业务规则。

### 3.3 可用性

- 快速入口按钮显式声明 `type="button"`，避免未来嵌入表单时产生隐式提交；
- 快速入口增加 `focus-visible` 状态；
- 非语义装饰图标使用 `aria-hidden`；
- Runtime 表格启用溢出提示；
- 移动端将活动摘要降为单列，避免窄屏拥挤。

## 4. 设计边界

1. Dashboard 仍然是聚合展示层，不承载 Webhook 投递、重试、租约、SSRF、Secret 等后端业务规则。
2. 不创建新的 Dashboard API。
3. 不把尚未稳定的 2.9-D destination/subscription Contract 提前映射成前端假数据或表单。
4. 测试只验证 UI 对 API 客户端返回值的展示，不复制生产计算逻辑。

## 5. 自动化测试

```powershell
cd frontend
npm test -- tests/views/Dashboard.test.ts
npm test
npm run build
npm run test:gate
```

## 6. 手动验证流程

```powershell
cd frontend
npm install
npm run dev
```

浏览器依次验证：

1. `/dashboard` 首次加载显示 Agent、可运行 Agent、Tool、Runtime、失败执行五项指标；
2. Runtime 有数据时，最近执行表格显示执行 ID、状态、Agent、耗时和开始时间；
3. 最近执行窗口摘要与当前拉取的最多 8 条记录一致；
4. 点击“查看全部”进入 `/runtime`；
5. 点击六个常用入口均进入对应页面；
6. 存在失败执行时显示告警并可进入 Runtime；
7. 点击“刷新数据”重新读取四组 API 数据；
8. API 失败时显示错误提示；
9. 浏览器缩放到窄屏，确认指标、活动摘要和入口无横向溢出；
10. 使用键盘 Tab 操作快速入口，确认存在可见焦点状态。

## 7. 验收记录

本次环境无法访问 GitHub 外部网络，无法在当前执行环境重新安装依赖并运行项目本地 Node/Vite/Vitest；因此不虚构“本地通过”结果。

开发者提供的上一轮结果为 `npm run build` 已通过，但 Dashboard 回归为 `88/89`，失败项仅为 `tests/views/Dashboard.test.ts`。提交后应以开发者本地实际执行上述四条命令的结果更新验收记录。
