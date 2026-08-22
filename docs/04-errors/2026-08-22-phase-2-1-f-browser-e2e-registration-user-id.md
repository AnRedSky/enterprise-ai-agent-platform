# Phase 2.1-F Browser E2E Registration User ID Error

## 1. 发生时间

2026-08-22

## 2. 场景

Phase 2.1-F Browser E2E Organization Management Gate。

## 3. 实际错误

Playwright 在添加成员步骤失败：

```text
locator.fill: value: expected string, got undefined

await page.getByRole("dialog").getByLabel("User ID").fill(memberUser.id);
```

## 4. 根因

`POST /auth/register` 的真实 API 响应字段是 `user_id`，不是 `id`。E2E 测试将注册响应错误地按通用 `id` 字段读取，因此传给 Playwright `fill()` 的值为 `undefined`。

后端 Auth Contract 明确返回：

```json
{"user_id": "...", "username": "...", "tenant_id": "...", "roles": ["user"]}
```

## 5. 修复

将 Organization Browser E2E 中成员用户标识统一改为 `memberUser.user_id`，并增加 `expect(memberUser.user_id).toBeTruthy()`，使测试直接遵守真实 Auth API Contract。

## 6. 验证状态

修复已直接提交 `main`：

```text
4ff9e9524ace10115298980f9d99ada3e6af1cb7
fix: use registration user_id in organization browser e2e
```

修复后的 Browser E2E 尚未由本地重新执行，因此本错误不能记录为已通过验证；必须重新运行 Phase 2.1-F Browser E2E Gate。
