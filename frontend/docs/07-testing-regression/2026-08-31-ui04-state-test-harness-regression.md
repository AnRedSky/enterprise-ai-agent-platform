# UI-04 状态测试 Harness 回归记录 — 2026-08-31

## 1. 基线

本轮开始前先将历史 `frontend` 分支快进同步到最新 `main`。`main` 最新提交为 `c7c1e53b155cb93559e035bee533d2ff293d757e`；其父提交即历史 `frontend` HEAD，因此不存在需要解决的代码冲突。

本地反馈集中在 Dashboard / Knowledge / Tool 三个 UI-04 状态测试：

- Dashboard：Error 重试后未触发第二次请求；未知 Execution 状态断言为空。
- Knowledge：Error 重试后未触发第二次请求。
- Tool：Error 重试后未触发第二次请求，并持续出现 `Failed to resolve directive: loading` 警告。
- `StatePanel.test.ts` 6/6 通过，说明公共状态组件本身的 action emit 契约正常。

## 2. 根因

生产页面已经通过 `StatePanel` 的 `action` 事件连接 `load` / `loadBases` 等恢复动作。问题位于页面测试 Harness：测试通过 `global.components` 注册 `StatePanel`，但页面使用的是 `<script setup>` 中直接导入的本地 `StatePanel`，因此该注册不能可靠覆盖本地组件。

结果是测试实际挂载了生产 `StatePanel`，其内部 `el-button` 又被测试替身处理，最终使测试对“状态面板按钮 → action → reload”的边界不稳定，表现为请求计数仍为 1。

Dashboard 的未知状态断言还缺少一次 DOM 更新同步点；状态映射本身已经按准则返回 `未知状态（技术值）`。

Tool 测试另外缺少 `v-loading` 指令测试替身，导致 Vue warning 污染测试输出。

## 3. 修复

### 3.1 StatePanel stub 改为显式 component stub

Dashboard / Knowledge / Tool 三个 UI-04 测试统一使用 `global.stubs.StatePanel`，确保测试明确替换页面本地导入的状态组件，并直接验证 `action` emit 到页面恢复函数的链路。

### 3.2 DOM 同步

Dashboard 未知 Execution 状态测试在异步请求完成后增加 `nextTick()`，避免在 Element Plus 表格完成下一轮 DOM 更新前读取文本。

### 3.3 Loading directive harness

Tool UI-04 测试增加 `global.directives.loading` 测试替身，避免测试因 Element Plus `v-loading` 指令缺失产生非业务 warning。

## 4. 业务边界

- 未修改 Dashboard / Knowledge / Tool 的生产业务逻辑。
- 未新增 API client、mapper 或状态枚举。
- 未改变 Backend Contract。
- 未将未知后端状态强制转换成已知状态。
- 未绕过权限、tenant boundary 或错误边界。
- 重试仍由页面已有的真实加载函数执行，不通过定时器或测试专用业务逻辑模拟。

## 5. 验证

针对本轮变更应执行：

```powershell
npm test -- tests/views/DashboardUI04.test.ts
npm test -- tests/views/KnowledgeUI04.test.ts
npm test -- tests/views/ToolUI04.test.ts
npm test -- tests/components/StatePanel.test.ts
npm test
npm run build
npm run test:gate
```

当前 GitHub 操作环境无法访问用户 Windows 工作树中的本地 npm 环境，因此以上命令不能被本轮远程代码操作宣称为“已通过”。最终验收状态保持为 **待本地验证**。

## 6. 本地复验要求

用户本地依赖环境无需启动后端服务；上述 UI 状态测试使用 Vitest mock 数据即可执行。不得通过 `npx` 临时下载测试框架，也不得手工填写测试数据。
