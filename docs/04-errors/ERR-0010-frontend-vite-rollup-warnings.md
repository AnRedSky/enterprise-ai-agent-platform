# ERR-0010 — Frontend Vite/Rollup 第三方依赖构建警告

- Legacy ID: `006-frontend-vite-rollup-third-party-pure-annotation-warning`
- Phase: 1.5-F

曾出现 VueUse PURE annotation、>500kB chunk、manualChunks circular chunk 与 Node localStorage warning。处理原则：不修改 node_modules、不全局静默 Rollup warning、不提高 `chunkSizeWarningLimit` 隐藏问题；按需注册 Element Plus、移除危险 manualChunks 边界、保留 route lazy loading，并在 tests/setup 提供确定性 storage。历史最终结果：12 test files / 37 tests passed，build 1705 modules，最大 JS chunk 340.37 kB，相关 warning 消失。
