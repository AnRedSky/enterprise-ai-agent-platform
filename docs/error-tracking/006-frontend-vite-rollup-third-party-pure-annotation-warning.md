# 006：Frontend Vite/Rollup 第三方依赖 PURE annotation 构建警告

## 发现阶段

Phase 1.5-F Vue Workflow / Governance 管理端

## 现象

开发者执行：

```powershell
cd frontend
npm run build
```

production build 成功，但 Vite/Rollup 曾输出两类主要 warning：

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

前端测试阶段还曾出现 Node 25+ `localStorage` ExperimentalWarning；该问题已由 `frontend/tests/setup.ts` 提供确定性的测试 storage 处理，不属于 production bundle 问题。

## 影响

这些 warning 均不会直接阻断 production build，但会降低构建输出的可读性，并可能掩盖真正的 bundle 体积问题。

## 根因判断

1. `@vueuse/core` 发布产物中的 `/* #__PURE__ */` 注释位置与当前 Rollup annotation 解析规则不完全兼容。
2. chunk size warning 来自前端 bundle 超过 Vite 默认 500 kB 提示阈值；此前 Element Plus 使用 `app.use(ElementPlus)` 全量注册，使 `element-plus-vendor` 成为主要大 chunk。
3. Node `localStorage` warning 来自测试运行环境访问 Node 25+ guarded global localStorage accessor。

## 已实施处理

### PURE annotation

- 不直接修改 `node_modules/@vueuse/core`。
- Vite `rollupOptions.onwarn` 仅过滤 `INVALID_ANNOTATION` 且消息明确指向 `@vueuse/core` 的已知 warning。
- 其他 Rollup warning 继续交给默认处理器，不进行全局静默。

### Bundle / chunk

- 保留 route-level lazy loading。
- 保留已有 `manualChunks` vendor 拆分策略。
- 移除 `main.ts` 的 `app.use(ElementPlus)` 全量注册。
- 按当前页面实际使用情况手工注册 Element Plus 组件，利用 Element Plus ES Module Tree Shaking 降低 JS bundle。
- 不通过提高 `chunkSizeWarningLimit` 掩盖 bundle 体积问题。
- Element Plus 全局 CSS 暂时保持不变，避免本轮构建优化引入样式行为变化。

### localStorage

- `frontend/tests/setup.ts` 在测试初始化阶段提供确定性的 `Storage` 实现。
- 测试前清理 storage，避免依赖 Node 进程参数。

## 验证要求

整改提交后由开发者本地执行：

```powershell
cd frontend
npm test
npm run build
```

重点确认：

- Vitest 通过且不再出现 Node `localStorage` ExperimentalWarning。
- production build 通过。
- 不再出现 `@vueuse/core` PURE annotation warning。
- Element Plus JS vendor chunk 明显下降；若仍超过 500 kB，应继续做实际 bundle 分析，而不是提高 warning 阈值。
- 其他 Rollup warning 必须逐项解释。

## 当前状态

前端构建优化代码已提交，等待开发者本地执行 `npm test` 与 `npm run build` 进行最终验收；在验收反馈前，本记录不将 Phase 1.5-F 标记为正式完成。
