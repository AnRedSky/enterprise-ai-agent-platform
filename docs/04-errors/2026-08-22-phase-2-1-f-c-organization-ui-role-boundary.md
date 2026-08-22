# Phase 2.1-F-C Organization UI Role Boundary

## 1. 发现问题

在 2.1-F-C Governance Browser Acceptance 实现前核查 Organization Detail 时发现，前端原实现使用：

```ts
const canManage = computed(() => true);
```

因此普通 `member` 以及 Owner Transfer 后已经降级为 `admin` 的旧 Owner，理论上仍会看到全部 Organization 管理操作；其中 `transfer-owner` 后端明确要求当前角色必须是 `owner`，形成前后端权限边界不一致。

## 2. 根因

Organization Detail 前端没有持久化当前登录用户身份，也没有根据当前 Organization Membership 判断 UI 能力；后端已经按照 OrganizationMembership 的 `owner/admin/member` 与 `active/suspended` 状态执行授权。

## 3. 修复

- `/auth/login` 响应增加 `user_id`，保持现有 token/roles/tenant_id 合同不变。
- 前端 Auth Session 持久化 `user_id`。
- Organization Detail 根据当前用户对应 membership：
  - `owner/admin + active` → Organization / Membership 管理 UI 可见；
  - `member` 或非 active → 管理 UI 隐藏；
  - `transfer-owner` 仅 `owner + active` 可见。
- 保留后端授权作为最终安全边界，前端控制只负责 UI capability boundary。

## 4. 自动化覆盖

新增/调整：

- Auth session user id unit test。
- Organization Detail member UI boundary test。
- Owner Transfer 后旧 Owner / 新 Owner boundary test。
- Browser E2E：Member boundary、Suspended member blocking、Owner Transfer boundary。

## 5. 验证状态

用户已验证原 F-A/F-B Organization Browser E2E：

```text
1 passed (8.7s)
```

F-C 新增场景尚未由用户本地真实 Browser Gate 执行，必须在 Gate 执行后才能标记 Passed。
