# UI-04 Core Regression

## 目标

在七个真实页面完成 UI-04 公共状态迁移后，统一验证 `StatePanel` 五态、403 Permission、Error Retry、Empty 操作入口、Success 数据展示及测试装配稳定性。

## 2026-08-31 本轮本地反馈修复

用户本地回归基线：45 个测试文件中 11 个失败，186 个测试中 10 个失败；Frontend regression gate 因此阻塞。本轮只修复反馈中已确认的测试契约/装配问题，不修改后端 Contract，不新增业务状态机。

### 根因与修复

1. **Vitest Mock hoisting / TDZ**
   - `AgentUI04.test.ts`、`AuditLogUI04.test.ts`、`RuntimeUI04.test.ts`、`Tools.test.ts` 在 `vi.mock()` factory 中直接引用文件顶层 `vi.fn()`。
   - Vitest 会提升 `vi.mock()`，导致 `Cannot access ... before initialization`。
   - 统一改为 `vi.hoisted(() => ({ ... }))` 创建 Mock，并由 factory 返回 hoisted 对象。

2. **Element Plus bootstrap mock 不完整**
   - `main.test.ts` 未提供 `ElIcon`，而 `src/main.ts` 已将 `ElIcon` 注册为全局组件。
   - 补齐 `ElIcon` mock，保持 bootstrap 测试只验证全局 loading directive 注册，不扩大真实组件加载范围。

3. **Agent runtime identifier 测试等待条件错误**
   - 原测试以“系统提示词”文本作为 Chat context 完成条件，但测试用 Dialog stub 同时渲染创建表单，因此该文本并不能证明 Chat context 已加载。
   - 改为等待 `chatContextState === "success"` 后再验证请求标识、链路追踪标识、会话标识和执行标识。

4. **AuditLog 状态选择器与公共组件 Contract 脱节**
   - 页面已经统一使用 `StatePanel`，其稳定 DOM 状态类为 `.state-panel--empty` / `.state-panel--error`，旧测试仍寻找 `.empty` / `.alert`。
   - 测试改为通过公共状态 class 验证 Empty/Error，同时保留用户可见中文文案和不暴露后端原始异常的断言。

5. **Dashboard / Knowledge UI-03 测试过度依赖 shallow stub 文本**
   - `PageHeader`、`SurfaceCard`、`StatePanel` 被 shallow mount 自动 stub 后，组件内部标题/description 不会进入 `wrapper.text()`，导致“实际组件存在且 props 正确”却出现空文本失败。
   - Dashboard 改为显式 stub 共享组件并验证 `PageHeader` / `SurfaceCard` props；Knowledge 改为显式 stub `PageHeader` / `StatePanel` 并验证状态 props。
   - Dashboard Empty 测试保留真实 Empty 文案与快速入口验证。

6. **Operations Console Audit Tab 未激活**
   - Element Plus Tabs 默认只渲染当前激活面板，旧测试在默认 Global Tab 下直接查找 Audit 输入 placeholder。
   - 测试先将 `activeTab` 设置为 `audit`，再验证 tenant-scoped audit query 参数与筛选 UI。

7. **Agent UI-04 对话调试 Permission 回归的 Mock 生命周期不稳定**
   - 最新本地反馈中，五个 targeted 页面文件共 21 个测试仅 `AgentUI04.test.ts` 的 1 个测试失败：点击“对话调试”后 `chatContextState` 仍为 `empty`，预期为 `permission`。
   - `AgentUI04.test.ts` 原先在 `beforeEach` 使用 `vi.clearAllMocks()`。该 API 只清理调用历史，不会重置 mock implementation 或一次性 `mock*Once` 行为；在包含未完成异步 Mock 的测试文件中，这会留下不必要的跨用例状态风险。
   - 改为 `vi.resetAllMocks()`，在每个用例开始时同时清理调用历史和 mock implementation/once 队列。
   - 对话调试回归增加明确的异步等待顺序：先等待 `getPublishedVersion("a1")` 确认点击事件已经真正进入 API 调用，再等待 `chatContextState === "permission"`，最后验证用户可见的“无权加载调试配置”。
   - 生产代码的 403 → Permission 映射保持单一实现：`loadChatContext()` 通过 `isPermissionError()` 将 HTTP 403 映射为 `permission`，非 403 仍映射为 `error`，不新增第二套状态机。

## 本轮修改文件

- `tests/views/AgentUI04.test.ts`
- `tests/views/AuditLogUI04.test.ts`
- `tests/views/RuntimeUI04.test.ts`
- `tests/views/Tools.test.ts`
- `tests/main.test.ts`
- `tests/views/Agents.test.ts`
- `tests/views/AuditLog.test.ts`
- `tests/views/DashboardUI03.test.ts`
- `tests/views/KnowledgeUI03.test.ts`
- `tests/views/OperationsConsole.test.ts`

## 2026-09-01 本地回归反馈

用户本地执行：

```powershell
npm run test:unit -- --run tests/views/AgentUI04.test.ts tests/views/AuditLogUI04.test.ts tests/views/Dashboard.test.ts tests/views/Tools.test.ts tests/views/OperationsConsole.test.ts
```

结果：4 个测试文件通过，`AgentUI04.test.ts` 仍有 1 个失败；共 5 个测试文件、21 个测试，20 个通过、1 个失败。

失败项：

```text
AgentUI04.test.ts > AgentWorkbench UI-04 > separates chat context permission from chat context error
Expected: permission
Received: empty
```

本次修复针对该测试的 Mock 生命周期与异步断言顺序。由于当前执行环境没有 Node/Vitest，修复后的结果不能由远端工具代替用户本地执行，因此暂不标记为通过。

## 设计与实现约束

- 不修改 Backend Contract。
- 不复制业务状态机到测试或页面。
- `StatePanel` 继续作为 Loading / Empty / Error / Permission / Success 单一公共状态实现。
- 测试应验证公共组件 Contract、props、用户可见文案和关键行为，不依赖被 stub 子组件的内部实现细节。
- Mock 必须在 `vi.mock()` hoisting 规则下安全初始化；跨用例状态使用显式 reset 策略。
- 异步行为测试必须先确认关键副作用已经发生，再等待最终 UI 状态，避免把“事件没有触发”和“状态映射错误”混为一个失败。
- 不把后端原始异常、HTTP body 或异常堆栈暴露给用户。

## 验证命令

```powershell
cd frontend
npm run test:unit -- --run tests/views/AgentUI04.test.ts tests/views/AuditLogUI04.test.ts tests/views/Dashboard.test.ts tests/views/Tools.test.ts tests/views/OperationsConsole.test.ts
npm test
npm run build
npm run test:gate
npm run test:final
```

## 当前事实

本轮已完成 GitHub 远端源码审查、main → frontend 快进同步、Contract 对齐和针对最新本地反馈的测试修复提交。当前执行环境没有可用的 Node/Vitest 运行环境，因此**不能将修复后的 targeted/full Vitest、build、gate 或 final 标记为通过**。GitHub Actions 也未提供可用于替代本地验收的 workflow run。

完成 UI-04 的判定仍必须以用户本地实际命令退出码为准：targeted → full → build → `test:gate` → `test:final`。

## 已知限制

- 本轮未启动 API、Scheduler、Worker、PostgreSQL、Redis。
- 本轮未自动生成或写入业务测试数据。
- Real API / Browser E2E 仍需在本地依赖和服务准备完成后按项目既定流程执行。

## 完成条件

只有 targeted + full Vitest、build、`test:gate`、`test:final` 均实际通过后，UI-04 才可从“进行中”更新为“已完成”，随后进入 UI-05 Form / Dialog / Drawer / Confirm 统一。
