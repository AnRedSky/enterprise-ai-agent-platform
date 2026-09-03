# Frontend Full Vitest Regression Remediation — 2026-08-30 / 2026-09-03

## 1. 历史基线

`main` 与 `frontend` 已通过合并提交同步；2026-09-03 的最新 `main` 已包含 Delegation Real API 并发 Fixture 事务边界修复，随后合入 `frontend`。

2026-08-30 的本地基线为 34 个测试文件中 2 个失败、153 个测试中 2 个失败，集中在 Runtime Operations 页面异步渲染与诊断错误可见性。

## 2. 2026-09-03 本地反馈

用户本地 `frontend` 执行：

```powershell
npm run test:unit
```

结果：

```text
Test Files  11 failed | 57 passed (68)
Tests       16 failed | 301 passed (317)
Duration    9.75s
```

本轮反馈暴露的失败可以归纳为四类：

1. **Runtime Correlations 静态契约测试与当前实现变量命名不一致**：测试要求 `audit.workflow_execution_id`，当前实现使用 `focusedAudit.workflow_execution_id` 与 `resolvedFact as RuntimeCorrelationAudit`，实际 durable fact 已存在且没有数组位置推断。
2. **Integrations 空状态测试未切换到订阅 Tab**：测试在默认投递目标 Tab 中查找“新建事件订阅”，因此无法找到该入口；生产页面已经通过 `:disabled="!destinations.length"` 正确禁用订阅创建。
3. **Integrations secret 回归测试断言错误**：`secret_ref` 本身包含字符串 `secret`，原断言 `"secret_ref".not.toContain("secret")` 在语义上不成立。应验证 secret reference 存在、secret plaintext 字段不存在，并确认页面不会展示密钥明文。
4. **Operations / Organizations 测试与当前 UI 文案不一致**：Operations 已将页面标题收敛为“运维窗口”，测试仍断言旧标题“Runtime 企业运维中心”；Audit Tab 测试依赖 Element Plus 内部 DOM class；Organizations 的当前实现保留了 `active/suspended` 技术值，测试则要求纯中文状态标签。

## 3. 本轮修复

### 3.1 Runtime Correlations

将静态契约断言改为检查实际 durable fact 展示路径 `focusedAudit.workflow_execution_id`，不放宽关系约束，也不增加任何 UI 推断。

### 3.2 Integrations

空状态测试在验证订阅创建入口前显式切换 `activeTab = "subscriptions"`，使测试操作真实用户路径而不是依赖默认 Tab。

Secret 回归测试改为读取实际 View 源码并验证：

- `secret_ref` 是允许的安全引用字段；
- 不存在 `secret:` 明文字段；
- 不读取 `.secret`；
- 页面明确声明不保存或展示密钥明文。

### 3.3 Operations Console

测试调整为当前已实现的“运维窗口”页面标题；Audit 查询测试通过 Vue 状态切换到 `audit` Tab，避免绑定 Element Plus 内部 DOM 结构；全局 Tab 测试直接验证 `ElTabPane` 的正式 `label` Props。

`NO_DURABLE_HEARTBEAT_FACT` 保持作为后端诊断 reason code 展示，测试验证该 durable diagnostic fact，而不是把它伪装成 Worker/Scheduler 已存活状态。

### 3.4 Organizations

组织状态映射调整为用户可见的纯中文：

- `active` → `已启用`
- `suspended` → `已暂停`
- 未知值 → `未知状态（技术值）`

保持后端状态枚举不变，只调整展示层映射。

## 4. 版本同步事实

本轮开始时 `frontend` 已与当时 `main` 同步；开发过程中 `main` 又新增 Delegation 事务边界相关提交。已创建并合并 `main → frontend` 同步 PR，最终 `frontend` HEAD：

`b46c58e4c8e9101f7ccc26a22ca1a0d67886d2c7`

最终 `frontend` 相对 `main`：

- `behind_by = 0`
- `ahead_by = 6`

说明最新 Backend Contract / regression fixture 已进入前端开发基线。

## 5. 验证状态

由于当前 ChatGPT 执行环境无法访问用户 Windows 工作树，也无法安装项目依赖或直接执行用户机器上的 `npm run test:unit`，本轮没有伪造本地通过结果。

用户本地反馈仍是本轮修复前的基线：**16 failed / 301 passed / 317 total**。上述代码修复已提交到 `frontend`，但必须由用户在同步后的本地工作树重新执行验证。

标准验证顺序：

```powershell
npm test -- tests/views/FullSiteConsistencyStaticAudit.test.ts tests/views/Integrations.test.ts tests/views/IntegrationsUI03UI05.test.ts tests/views/OperationsConsole.test.ts tests/views/Organizations.test.ts
npm run test:unit
npm run build
npm run test:gate
```

需要真实浏览器验证时再执行：

```powershell
npm run test:e2e
```

项目已有 `frontend/scripts/test/` 下的自动化脚本负责完整回归；测试不得自动启动 API、Scheduler、Worker、PostgreSQL 或 Redis，测试数据由 Fixture 自动生成。

## 6. 当前状态

**代码修复已完成，待本地验证。**

不能将本轮状态标记为“全量通过”，直到用户本地重新执行 `npm run test:unit`、`npm run build` 和 `npm run test:gate` 并提供实际结果。