# 2026-08-29 Frontend DeliveryConsole 异步回归竞态

## 现象

`frontend/tests/views/DeliveryConsole.test.ts` 的首个测试在 Delivery 数据通过 mocked API 异步加载后，期望页面展示 `HTTP_ERROR`、`Replay`、`Audit`。实际测试反馈为“暂无 Delivery 记录”。

## 根因

测试使用 `await vi.waitFor(() => expect(wrapper.text()).toContain("失败"))` 作为数据加载同步点，但“失败”同时存在于静态摘要标题“失败 / 死信”中，因此该断言可能在 `integrationApi.deliveries()` 完成之前立即成功。随后对 `HTTP_ERROR` 的同步断言存在竞态。

## 修复

将等待条件改为真正依赖异步 Delivery 数据的 `HTTP_ERROR`，并继续使用完整 `ElementPlus` 插件装配。这样测试只会在模拟 API 数据完成加载且表格行渲染后继续执行。

## 影响范围

仅影响 Frontend Vitest 回归测试同步点，不修改 Delivery API、生产 UI、Replay 或 Audit 业务逻辑。

## 验证命令

```powershell
cd frontend
npm test -- tests/views/DeliveryConsole.test.ts
npm test
npm run build
npm run test:gate
```

以上命令需要在项目本地 Windows 环境实际执行后才能记录最终通过状态。