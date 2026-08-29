# ERR-0031 Frontend SSE Reader Double 与 Runtime Status Contract 漂移

## 现象

2026-08-29 开发者本地 Frontend `npm test`：19 个测试文件中 17 个通过、2 个失败；86 个测试中 82 个通过、4 个失败。

失败分为两类：

1. `tests/api/chat.test.ts` 的 3 个 SSE 测试在 `reader.releaseLock()` 处失败：`TypeError: reader.releaseLock is not a function`。
2. `tests/views/Runtime.test.ts` 的 Runtime Execution 使用后端 `status: success`，前端显示“未知”，测试期待“已完成”。

同时发现 Agents 与 Workflow Triggers 测试的 Element Plus 测试桩不完整，产生 `el-tag` / `el-empty` 未解析 warning。

## 根因

### SSE

生产 `streamChat()` 使用标准 Fetch `ReadableStreamDefaultReader`，在 `finally` 中释放 Reader。测试 Double 只模拟了 `read()`，没有模拟标准 Reader 的 `releaseLock()` 生命周期方法。问题属于测试 Double Contract 漂移，不应通过删除生产资源释放逻辑规避。

### Runtime Status

Runtime 数据中的成功状态可以表示为 `success`；前端状态归一化只注册了 `completed`，因此 `success` 被错误降级为 `unknown`。问题属于公共 Runtime 展示 Contract 的别名缺失。

## 修复

- SSE 测试 Double 增加 `releaseLock` mock。
- `normalizeRuntimeStatus()` 增加 `success` 与 `succeeded` 到 `completed` 的统一映射。
- Runtime View 增加状态别名回归测试。
- Agents 测试补齐 `el-tag` stub。
- Workflow Triggers 测试补齐 `el-empty` stub。
- 修复过程与本地验收命令记录在 `frontend/docs/PHASE_2_9_FRONTEND_REGRESSION_FIX.md`。

## 预防

1. Fetch/Stream 相关测试 Double 必须保持浏览器标准对象的关键生命周期方法。
2. Runtime 状态别名统一在 `src/utils/runtime.ts` 归一化，不允许页面级重复判断。
3. Vue 单元测试必须显式 stub 使用到的 Element Plus 组件，避免 warning 淹没真正失败。
4. 每次本地回归失败都必须区分代码根因、测试基础设施根因和环境问题，并记录实际验证边界。

## 验证边界

本记录基于开发者提供的真实本地 `npm test` 输出创建。修复代码提交后，必须重新执行 Frontend Test、Production Build 和 Frontend Regression Gate；在获得新的实际输出前，不宣称修复后已通过。
