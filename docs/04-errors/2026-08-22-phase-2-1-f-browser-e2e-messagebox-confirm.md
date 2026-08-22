# Phase 2.1-F Browser E2E MessageBox Confirmation Error

## 1. 发生时间

2026-08-22

## 2. 场景

Phase 2.1-F Browser E2E Organization Management Gate。

## 3. 实际错误

组织暂停步骤中 Playwright 在 Element Plus MessageBox 内使用角色定位确认按钮超时：

```text
Test timeout of 60000ms exceeded.

Error: locator.click: Test timeout of 60000ms exceeded.
Call log:
- waiting for locator('.el-message-box:visible').getByRole('button', { name: '确定' })
```

## 4. 根因

这是 Browser E2E 测试实现的定位脆弱性。真实页面已经打开可见的 Element Plus MessageBox，但测试依赖 MessageBox 内部按钮的 accessible role/name 解析结果。该解析在当前真实浏览器运行环境下没有稳定匹配 `确定`，导致测试等待到 60 秒超时。

业务流程本身尚未出现 HTTP 或后端错误；失败发生在确认操作执行前。

## 5. 修复

将组织暂停、组织恢复和 Owner Transfer 的 MessageBox 确认按钮定位统一改为当前可见 MessageBox 内的 Element Plus primary confirmation button：

```ts
const confirm = dialog.locator(".el-message-box__btns .el-button--primary");
await expect(confirm).toBeVisible();
await confirm.click();
```

同时保留对 MessageBox 文本内容的断言，避免脱离真实业务提示而仅依赖 CSS 定位。

## 6. 验证状态

修复已直接提交 `main`：

```text
fe2226d3078c319713228637304191935d227182
fix: remove brittle message box role lookup
```

修复后的 Browser E2E 尚未由本地重新执行，因此本错误不能记录为已通过验证；必须重新运行 Phase 2.1-F Browser E2E Gate。
