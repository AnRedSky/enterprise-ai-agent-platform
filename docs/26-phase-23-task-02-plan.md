# 26 - Phase 23 Task 02 规划

## 1. 目标

建立前端 Runtime 管理页面的最小自动化测试基础，并在不改变业务行为的前提下验证核心状态流转。

## 2. 执行顺序

1. 增加 Vitest / Vue Test Utils 测试依赖与配置。
2. 为 Runtime API Client 建立可 mock 的请求边界。
3. 覆盖 Runtime List：Loading、Success、Empty、Error。
4. 覆盖 Audit List：Loading、Success、Empty、Error。
5. 覆盖 Pagination / Status Filter 请求参数。
6. 执行 frontend typecheck/build/test。

## 3. 完成标准

- 测试配置进入仓库。
- 核心 Runtime / Audit 页面至少具备上述状态测试。
- 不提交 node_modules、dist、coverage 等构建产物。
- 完成后必须新增下一阶段完成记录和下一任务规划文档，并与代码提交。

## 4. 风险

当前 `frontend/package.json` 尚未配置测试脚本；Task 02 首先解决测试工具链缺口，再进入组件测试。
