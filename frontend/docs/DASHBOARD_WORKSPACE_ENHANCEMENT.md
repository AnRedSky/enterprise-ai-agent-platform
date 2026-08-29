# 前端工作台增强设计记录

## 1. 基线

- 基线分支：`main`
- 基线提交：`e05bf8eb`
- 当前前端自动化回归：89/89 通过
- 当前生产构建：通过
- Backend 当前仍处于 Phase 2.9-C Reliable Delivery 第二切片真实 PostgreSQL 验收阶段，2.9-D Webhook Integration 尚未进入实现阶段。

## 2. 本次交付

本次不提前假设 2.9-D Webhook Contract 已稳定，而是先增强现有 Dashboard，使其成为真实可用的企业平台入口：

1. 保留现有 Agent、Tool、Runtime 真实 API 指标；
2. 将 Runtime 总量查询扩展为最近 8 条真实执行记录，同时保留失败数量查询；
3. 增加执行状态、Agent、耗时、开始时间等运行态摘要；
4. 增加 Agent、Tool、知识库、工作流、Runtime、审计日志六个业务入口；
5. 失败执行数量大于 0 时提供明确的 Runtime 处理入口；
6. 保持所有数据来自既有 API，不创建并行 API 或 mock 生产数据；
7. 保持 Dashboard、Runtime、Agent 等领域边界，不把事件投递逻辑提前复制到前端。

## 3. 设计决策

### 3.1 Dashboard 只做聚合展示

Dashboard 负责并行读取既有领域 API 并进行轻量展示转换，不新增业务规则。Agent 发布、Tool 治理、Workflow 编排、Runtime Trace 等操作继续由对应页面负责。

### 3.2 Runtime 活动优先使用既有分页接口

后端已经提供 `GET /runtime/executions` 分页接口，因此最近执行直接使用 `page=1&page_size=8`，避免新增 Dashboard 专用后端接口。

### 3.3 失败状态必须可操作

失败数量不是装饰性指标。存在失败执行时，Dashboard 明确引导到 Runtime 页面，形成“发现问题 → 查看执行 → 处理问题”的闭环。

### 3.4 响应式布局

桌面端采用指标卡 + 活动列表 + 快速入口双栏布局；中小屏自动降为单栏，避免企业管理页面在窄窗口中产生横向滚动。

## 4. 测试策略

Dashboard 测试验证：

- Agent / Tool / Runtime 三类真实 API 客户端调用被正确聚合；
- Runtime 最近执行记录被渲染；
- 失败数量被渲染；
- 快速业务入口存在；
- API 异常时展示明确错误。

不在 Dashboard 单测中复制 Runtime、Agent 或 Tool 的生产算法。

## 5. 验收命令

```powershell
cd frontend
npm test -- tests/views/Dashboard.test.ts
npm test
npm run build
npm run test:gate
```

Browser E2E 如覆盖 Dashboard，则单独执行既有 Browser Gate，不将 Backend、Frontend regression 和 Browser E2E 合并为一个 Gate。
