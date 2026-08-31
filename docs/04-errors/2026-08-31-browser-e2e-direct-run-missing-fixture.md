# 2026-08-31 Browser E2E 直接 Runner 缺失 Fixture 导致 Owner Login 失败

## 现象

本地直接执行：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend
npm run test:e2e
```

结果为 8 个 Browser E2E 中 5 个失败、3 个通过。失败测试全部在 Organization / Model Provider owner 场景的 `loginOwner()` 处失败，断言 `POST /api/v1/auth/login` 的 `response.ok()` 为 `false`。

## 根因

Organization 与 Model Provider owner E2E 使用真实 owner 账号 `browser_e2e_owner`。该账号不是普通注册流程自动产生的 owner；它由 `backend/scripts/test/e2e/00_reset_browser_e2e_database.py` 在 Browser E2E 场景隔离前创建，并同时建立 active Organization 与 owner membership。

`npm run test:e2e` 只是原始 Playwright runner，不会执行数据库 reset，因此在未建立 fixture 的普通本地数据库上，owner 登录失败是预期的前置条件错误，不是 Organization / Model Provider UI 或 Backend Contract 的新回归。

## 影响

- Organization 3 个 owner/member governance 测试无法进入业务断言；
- Model Provider 2 个测试无法进入 owner/member UI 断言；
- 已通过的 Workflow Trigger / Webhook 测试说明当前失败并非全局 Browser runtime 不可用。

## 修复

1. 将 `frontend/scripts/test/run-local-full-regression.ps1` 的 Browser E2E 阶段改为 isolated scenario runner。
2. Organization、Model Provider、Workflow Trigger、Webhook Governance、Webhook Runtime 均在独立场景前自动执行 fixture reset。
3. 保留 `npm run test:e2e` 为低层 Playwright runner，不让它隐式清理开发者本地数据库。
4. 文档统一使用 `03_run_model_provider_e2e.ps1` 作为 Model Provider isolated gate。

## 防回归规则

- Full Regression 不得直接调用原始 `npm run test:e2e`。
- Owner-only Browser E2E 必须通过 isolated runner 建立 deterministic owner fixture。
- 测试数据必须由脚本生成，禁止开发者手工填写 owner、Organization、Membership 或业务 ID。
- 未执行 fixture reset 的直接 runner 失败不得记录为产品功能失败。

## 验证

本次仅完成 GitHub-side 代码与文档修复。由于当前工作区无法访问用户本地 Windows Backend / Frontend 服务，不宣称 Browser E2E 已通过。下一步使用：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend
npm run test:local:full
```

以实际本地输出完成验收。
