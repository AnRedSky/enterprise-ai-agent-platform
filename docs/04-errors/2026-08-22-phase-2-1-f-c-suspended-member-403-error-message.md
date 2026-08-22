# Phase 2.1-F-C Suspended Member Browser 403 Error Message

## 1. 现象

用户本地执行 Phase 2.1 Organization Browser E2E 时，前两个/第三个场景结果为 2 passed、1 failed。

失败场景：

```text
Organization browser governance enforces member and suspended-member boundaries
```

失败断言：

```text
Expected substring: "Organization 详情加载失败"
Received string:    "Request failed with status code 403"
```

失败位置：

```text
frontend/tests/e2e/organization-management.spec.ts:190
```

## 2. 根因

Backend 对 suspended member 的 Organization Detail 访问返回 HTTP 403，这是正确的后端授权结果；Frontend `OrganizationDetail.load()` 直接使用 Axios `Error.message` 作为 UI alert 文案。

因此浏览器收到 403 后展示 Axios 默认错误文本，而没有遵循 Organization Detail 的前端错误文案契约。

## 3. 修复

`frontend/src/views/organizations/detail.vue` 增加 `organizationLoadError()`，按 HTTP 状态将授权/不存在错误归一化为稳定的业务文案：

- 403：`Organization 详情加载失败：当前用户无权访问该 Organization。`
- 404：`Organization 详情加载失败：Organization 不存在或已不可访问。`
- 其他异常：`Organization 详情加载失败`

这样既保留后端 403 授权语义，又避免把 Axios 内部错误文本直接暴露给用户，并满足 E2E 对稳定业务文案的断言。

## 4. 验证状态

用户报告的原始失败已经完成分析；修复提交后尚未由本地真实浏览器重新执行，因此本错误在重新执行前不得标记为已验证修复。

下一步：重新执行 Phase 2.1-F-C Organization Browser E2E；若通过，再执行 Frontend Regression + Production Build、Backend Regression、Real API Gate，并更新 Phase 2.1 Acceptance。
