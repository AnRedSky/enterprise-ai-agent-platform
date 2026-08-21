# ERR-0007 — Playwright Desktop Chrome Project 未定义

- Legacy ID: `004-playwright-project-missing`
- Phase: 1.6-C

E2E Gate 使用 `--project="Desktop Chrome"`，但 `playwright.config.ts` 未在 `projects[]` 声明该名称，导致测试启动前失败。Chromium 已安装，问题属于配置契约。修复为显式定义 `projects: [{ name: "Desktop Chrome", use: ... }]`；正式 Browser Gate 必须重新执行后才能判定通过。
