# Frontend Full Vitest / Browser E2E Regression Remediation — 2026-08-30 / 2026-09-04

## 1. 版本同步与当前基线

2026-09-04 已重新检查远端 `main` 与 `frontend`。最新 `main` 已通过 PR #92 合并进入 `frontend`。

```text
main    f435546ffb84229e8aae08fc5958ad24f295099b
frontend 2018514f58b2e6c562ce0ffd86182ed8edfc5291
关系：ahead 1 / behind 0
```

本轮 `main` 新增 Browser E2E 数据库隔离与 owner fixture 初始化脚本 `backend/scripts/test/e2e/00_reset_browser_e2e_database.py`。该脚本会清理 Organization 聚合，并重新建立 deterministic active owner fixture；不启动或停止任何服务。fileciteturn697file0L2-L2

## 2. 用户最新 Browser E2E 反馈

用户在 Windows `frontend` 工作树执行：

```text
npm run test:e2e -- tests/e2e/organization-management.spec.ts

2 failed / 1 passed (1.1m)
```

失败 1：owner browser contract 在已找到成员 row 后，点击 `编辑` 超时。

失败 2：owner transfer 场景前置条件发现持久 owner fixture 当前实际 membership 为 `active/admin`，而不是后端 Contract 要求的 `active/owner`。

同时已有基线保持：

```text
workflow-trigger-governance.spec.ts  1 passed (4.7s)
model-provider-governance.spec.ts    2 passed (9.3s)
```

## 3. 根因分析

### 3.1 当前主要阻塞是本地 Browser E2E 数据库状态漂移

最新后端已经提供专用 Browser E2E 数据库 reset 工具。该工具会：

1. `TRUNCATE TABLE organizations CASCADE` 清理 Organization 聚合及级联数据；
2. 确保 `DEFAULT_TENANT_ID` 存在且 active；
3. 确保 `BROWSER_E2E_OWNER_USERNAME/PASSWORD` 对应用户存在且 active；
4. 重新创建 `Browser E2E Organization`；
5. 将该用户重新建立为唯一 `active/owner` membership。fileciteturn697file0L2-L2

因此用户本轮第三个场景报告的 `admin` 状态不是前端权限逻辑应被放宽的证据，而是持久测试数据库未恢复到 deterministic owner fixture 基线。

### 3.2 第一场景不继续放宽 selector

生产 Organization 详情页明确以 `user_id` 作为成员表第一列，并仅在当前用户 `active` 且 role 为 `owner/admin` 时渲染成员操作列；`owner` 行本身不显示编辑/暂停/转移按钮。fileciteturn685file0L2-L2

当前 E2E 已从 Element Plus 内部 wrapper selector 改为 semantic table row，并增加分页切换等待。下一步优先恢复 deterministic owner fixture 后重新验证该失败，而不是继续增加 timeout 或放宽 locator。

## 4. 当前代码状态

Organization E2E 已包含：

- 唯一随机测试成员；
- 真实 `/organizations` 查询；
- 真实 membership 分页查询；
- semantic table row locator；
- owner/target membership durable precondition；
- transfer API status/body 诊断；
- transfer 后恢复原 owner；
- suspended-member 场景结束恢复 active。

生产 Organization API Types 与页面均保持现有正式 Contract；Membership role 仍为 `owner/admin/member`，status 仍为 `active/suspended`。fileciteturn686file0L2-L2

## 5. 本地验证前置条件

必须先使用后端已有的 Browser E2E 数据库隔离工具恢复 deterministic fixture：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
uv run python .\scripts\test\e2e\00_reset_browser_e2e_database.py
```

预期输出：

```text
BROWSER_E2E_DATABASE_RESET_OK owner=browser_e2e_owner
```

该脚本只重置 Browser E2E Organization/owner 测试数据，不启动 API、Worker、Scheduler、PostgreSQL 或 Redis。fileciteturn697file0L2-L2

然后回到 frontend：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend
npm run test:e2e -- tests/e2e/organization-management.spec.ts
```

Organization 3/3 后再执行：

```powershell
npm run test:e2e -- tests/e2e/workflow-trigger-governance.spec.ts
npm run test:e2e -- tests/e2e/model-provider-governance.spec.ts
npm run test:e2e
npm test
npm run build
npm run test:gate
```

## 6. 手动验收重点

### Organization

- reset 后 owner fixture 为唯一 active owner；
- 新注册成员自动拥有 active membership；
- 成员表正确展示 User ID、role、status；
- 编辑角色、暂停/恢复成员成功；
- 暂停/恢复组织成功；
- owner transfer 成功且 durable state 正确；
- transfer 后新 owner 获得 owner-only 操作，原 owner 降级；
- 最终恢复原 owner，避免污染下一轮测试。

### Workflow / Model Provider

继续保持用户当前已验证的 Workflow 1/1、Model Provider 2/2 基线。

## 7. 当前状态

**Organization E2E 阻塞于本地持久 Browser E2E fixture 状态漂移，尚未重新执行 reset 后验证。**

当前不修改生产 Organization Service，不通过放宽 selector、增加任意 timeout、跳过 durable assertion 或忽略 owner precondition 制造假绿。

下一步唯一优先动作：执行 Browser E2E database reset，然后重新执行 Organization targeted E2E；只有 reset 后仍出现可重复的生产/UI Contract 错误，才继续修改代码。
