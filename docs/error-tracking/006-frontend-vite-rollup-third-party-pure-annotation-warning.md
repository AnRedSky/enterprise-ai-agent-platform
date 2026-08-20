# 006：Frontend Vite/Rollup 第三方依赖 PURE annotation 构建警告

## 发现阶段

Phase 1.5-F Vue Workflow / Governance 管理端

## 现象

开发者执行：

```powershell
cd frontend
npm run build
```

production build 曾输出三类主要 warning：

```text
node_modules/@vueuse/core/dist/index.js (...): A comment
"/* #__PURE__ */"
contains an annotation that Rollup cannot interpret due to the position of the comment.
The comment will be removed to avoid issues.
```

以及：

```text
Some chunks are larger than 500 kB after minification.
Consider using dynamic import() to code-split the application.
```

前端测试阶段还曾出现 Node 25+ `localStorage` ExperimentalWarning；该问题已由 `frontend/tests/setup.ts` 提供确定性的测试 storage 处理，不属于 production bundle 问题。

## 影响

这些 warning 均不会直接阻断 production build，但会降低构建输出的可读性，并可能掩盖真正的 bundle 体积问题。

## 根因判断

1. `@vueuse/core` 发布产物中的 `/* #__PURE__ */` 注释位置与当前 Rollup annotation 解析规则不完全兼容。
2. chunk size warning 的第一轮主要原因是 Element Plus 使用全量注册/集中 vendor 拆分，导致 `element-plus-vendor` 成为约 900 kB 的单一 JS chunk。
3. Node `localStorage` warning 来自测试运行环境访问 Node 25+ guarded global localStorage accessor。
4. 第二轮取消 Element Plus 强制聚合后，构建暴露出新的 manual chunk 图问题：`vueuse-vendor -> vue-vendor -> vueuse-vendor` 以及 `vue-vendor -> element-plus-icons -> vue-vendor` 循环 chunk warning。

## 已实施处理

### PURE annotation

- 不直接修改 `node_modules/@vueuse/core`。
- Vite `rollupOptions.onwarn` 仅过滤 `INVALID_ANNOTATION` 且消息明确指向 `@vueuse/core` 的已知 warning。
- 其他 Rollup warning 继续交给默认处理器，不进行全局静默。

### Bundle / chunk 优化

- 保留 route-level lazy loading。
- 移除 `main.ts` 的 `app.use(ElementPlus)` 全量注册。
- 按当前页面实际使用情况手工注册 Element Plus 组件，利用 Element Plus ES Module Tree Shaking 降低 JS bundle。
- 移除 Vite `manualChunks` 中对 `element-plus` 的强制集中拆分，避免把按组件导入的 Element Plus 模块重新聚合成单一约 900 kB vendor chunk。
- 移除 `@vueuse` 与 `@element-plus/icons-vue` 的人工 `manualChunks` 边界，避免形成 circular chunk。
- 保留 Vue Router、Pinia、Axios、Vue 等相对稳定的 vendor 边界。
- 业务路由继续使用 lazy loading。
- VueUse、Element Plus icons 等依赖交由 Rollup 根据实际依赖图自然分配。
- 不通过提高 `chunkSizeWarningLimit` 掩盖 bundle 体积问题。
- Element Plus 全局 CSS 暂时保持不变，避免本轮构建优化引入样式行为变化。

### localStorage

- `frontend/tests/setup.ts` 在测试初始化阶段提供确定性的 `Storage` 实现。
- 测试前清理 storage，避免依赖 Node 进程参数。

## 最终验收结果

开发者第三轮反馈已经确认：

```text
npm test
12 test files passed
37 tests passed

npm run build
✓ 1705 modules transformed.
✓ built in 3.65s
```

production build 最终最大 JS chunk：

```text
index-DWNgX2PP.js  340.37 kB
gzip               114.62 kB
```

最终确认：

- Vitest 12 个测试文件全部通过。
- 37 个测试全部通过。
- Node `localStorage` ExperimentalWarning 已消失。
- `@vueuse/core` PURE annotation warning 已消失。
- Circular chunk warning 已消失。
- `>500 kB` chunk warning 已消失。
- Element Plus 不再生成约 900 kB 的单一 vendor chunk。
- 最大 JS chunk 为 340.37 kB，低于 Vite 默认 500 kB warning 阈值。
- production build 成功。
- 未通过提高 `chunkSizeWarningLimit` 隐藏问题。
- `tests / scripts` 职责隔离保持不变。

## 当前状态

**Phase 1.5-F 前端构建优化：验收通过。**

当前 vendor/chunk 策略正式收口：

- 不再继续人为拆分 VueUse、Element Plus icons 等依赖。
- 不再为了消除 warning 继续增加 vendor chunk 边界。
- 保留业务路由 lazy loading。
- 保留 Element Plus 按需注册。
- 仅保留稳定、无循环依赖风险的 vendor 边界。
- 后续如需进一步优化 bundle，应基于真实产物分析具体业务模块，而不是继续泛化 `manualChunks`。

本项整改完成后，继续推进 Phase 1.5-F 下一项工作，不重复创建测试入口，也不混用开发脚本与测试脚本。
