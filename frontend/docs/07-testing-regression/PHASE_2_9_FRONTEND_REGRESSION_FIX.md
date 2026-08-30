# 前端本地回归失败修复记录：SSE Reader 与 Runtime Status Contract

## 1. 基线

- `main`: `d0544ff5f24a1fbda8907fc90ac5fd4f299ce69a`
- 本次输入：开发者本地 `npm test` 结果
- 结果：19 个测试文件中 17 个通过、2 个失败；86 个测试中 82 个通过、4 个失败。

## 2. 问题一：SSE 测试 Double 缺少 `releaseLock`

### 现象

`tests/api/chat.test.ts` 的 3 个流式测试均在 `streamChat` finally 阶段失败：

```text
TypeError: reader.releaseLock is not a function
```

生产实现通过 `response.body.getReader()` 获得标准 `ReadableStreamDefaultReader`，结束时调用 `reader.releaseLock()`。当前测试 Double 只实现了 `read()`，没有实现标准 Reader 的资源释放方法，因此测试桩与浏览器 Fetch Contract 不一致。

### 根因

这是测试基础设施 Contract 漂移，不是 SSE 生产逻辑错误。生产代码已经正确执行跨 chunk parser、flush 和 AbortSignal；测试 Double 未覆盖 Reader 的必要生命周期方法。

### 修复

`frontend/tests/api/chat.test.ts` 的 `responseFromChunks()` 增加 `releaseLock` mock，并保留现有 `read()` 行为。这样测试可以继续验证真实生产路径的 `finally` 资源释放语义，而不是修改生产代码绕开测试错误。

## 3. 问题二：Runtime `success` 状态没有映射为前端“已完成”

### 现象

Runtime View 测试的 Execution 返回 `status: "success"`，页面实际显示“未知”，导致：

```text
Expected: 已完成
Received: ... 未知 ...
```

### 根因

后端 Runtime/Trace 数据允许使用 `success` 表达成功完成，而前端 `normalizeRuntimeStatus()` 只识别 `queued/running/completed/failed/cancelled/unknown`。因此成功数据落入 `unknown`。

### 修复

`frontend/src/utils/runtime.ts` 在统一状态归一化入口增加：

- `success` → `completed`
- `succeeded` → `completed`

展示层继续只有一个“已完成”正式状态，避免在各个 Vue 页面复制别名判断。

### 为什么放在 normalize 层

状态别名属于跨 API 数据展示 Contract，应该在 Runtime 基础工具层一次性归一化。页面只消费 `getRuntimeStatusMeta()`，不直接判断 `success`，从而避免后续新增 Runtime 页面产生第二套状态映射。

## 4. 测试噪声治理

同一次本地回归还发现两个测试文件产生重复的 Vue 未解析组件 warning：

- `Agents.test.ts`：`el-tag`
- `WorkflowTriggers.test.ts`：`el-empty`

这些不是业务失败，但会污染失败诊断输出。因此本次同步补齐测试桩，使测试环境显式声明所使用的 Element Plus 组件。

## 5. 本次验证范围

新增/调整测试覆盖：

1. SSE 跨网络 chunk 边界解析；
2. 无尾部分隔符的 SSE flush；
3. AbortSignal 透传；
4. SSE Reader `releaseLock` 生命周期；
5. Runtime `success` / `succeeded` → `已完成`；
6. Runtime Timeline / Workflow Trace；
7. Agents 与 Workflow Triggers 测试组件桩完整性。

## 6. 验收边界

本次修复依据开发者提供的真实 Windows 本地测试日志完成。修改提交后仍必须在开发者本地重新执行：

```powershell
cd frontend
npm test
npm run build
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

在没有新的实际命令输出之前，不将修复后的状态写成“本地回归通过”。

## 7. 原子提交

本次属于同一组本地回归失败的根因修复，代码、测试、错误记录和前端开发记录一次性进入同一个原子提交，不拆分中间提交。
