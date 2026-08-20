# 006：Frontend Vite/Rollup 第三方依赖 PURE annotation 构建警告

## 发现阶段

Phase 1.5-F Vue Workflow / Governance 管理端

## 现象

开发者执行：

```powershell
cd frontend
npm run build
```

production build 成功，但 Vite/Rollup 输出 2 类警告：

```text
node_modules/@vueuse/core/dist/index.js (...): A comment
"/* #__PURE__ */"
contains an annotation that Rollup cannot interpret due to the position of the comment.
The comment will be removed to avoid issues.
```

同时存在：

```text
Some chunks are larger than 500 kB after minification.
Consider using dynamic import() to code-split the application.
```

## 影响

当前没有阻断 production build：

```text
✓ 1704 modules transformed.
✓ built in 10.34s
```

因此当前属于可解释的构建 warning，不应直接修改 `node_modules`。

## 根因判断

1. `@vueuse/core` 发布产物中的 `/* #__PURE__ */` 注释位置与当前 Rollup 版本的 annotation 解析规则不完全兼容。
2. chunk size warning 是当前前端 bundle 体积超过 Vite 默认 500 kB 提示阈值导致，不等同于构建失败。

## 处理原则

- 不直接修改 `node_modules/@vueuse/core`。
- 不为了消除 warning 简单调高 `chunkSizeWarningLimit`，除非完成 bundle 分析并确认当前拆包策略合理。
- 优先在后续前端性能优化任务中评估 `dynamic import()` / route-level code splitting / `manualChunks`。
- 对第三方 PURE annotation warning，优先通过依赖版本升级、锁定兼容版本或构建链升级解决；在未验证兼容性前不盲目升级依赖。

## 当前结论

该 warning 已记录，暂不作为 Phase 1.5-F 功能验收阻塞项；production build 本身通过。

Phase 1.5-F 仍必须完成 Vitest、Backend regression、migration head verification 及手工联调后才能正式关闭。
