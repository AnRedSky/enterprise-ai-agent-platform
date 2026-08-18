# 44 - Phase 23 Task 09 下一阶段规划

## 1. 目标

完成 Frontend 测试修复后的人工验证闭环，并继续推进 Backend RBAC / Runtime 验证。测试环境由用户手动执行并反馈结果，开发侧不再假设本地测试已经通过。

## 2. 文档先行后的执行顺序

### Task 09-A：Frontend 验证

用户在 Windows 本地执行：

```bat
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend
npm test
npm run build
```

验收重点：

- Vitest 不再加载重复 `.test.js` 文件。
- `runtime.test.ts`、`AuditLog.test.ts`、`Runtime.test.ts` 全部被正常收集。
- 空态、错误态、Runtime Timeline 三类断言通过。
- 无 `Cannot access ... before initialization`。
- 无因测试环境缺少 Element Plus 组件 / `v-loading` 导致的失败。

### Task 09-B：Backend 验证

Frontend 通过后，用户手动执行：

```bat
cd ..\backend
pytest -q
pytest -q tests/test_runtime_http_rbac.py
pytest -q tests/test_runtime_rbac_matrix.py
```

### Task 09-C：结果处理

- 失败：记录完整错误、定位根因、补回归测试后提交修复。
- 通过：记录测试结果，进入下一项功能验收。
- 在所有关键测试通过前，不恢复 GitHub Actions 自动质量门禁，也不宣称 Phase 23 完成。

## 3. Git 提交规则

Task 09 完成时必须同时提交：

- `docs/45`：Task 09 完成记录；
- `docs/46`：下一阶段规划；
- 对应代码 / 测试变更。

所有开发继续基于 `main`，提交使用 Conventional Commits。禁止提交 `.env`、日志、构建产物、IDE 文件和其他非项目文件。