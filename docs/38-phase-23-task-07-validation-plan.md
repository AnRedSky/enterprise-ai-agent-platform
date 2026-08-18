# 38 - Phase 23 Task 07 测试验证与质量门禁规划

## 1. 目标

将 Phase 23 已编写的 frontend/backend 测试转化为可重复执行的质量证据，并集中修复实际失败。

## 2. 执行顺序

### Frontend

1. 安装 `frontend` 依赖。
2. 执行 `npm test`。
3. 修复 Vitest / Vue Test Utils / Element Plus mock、类型或组件问题。
4. 执行 `npm run build`。
5. 修复 vue-tsc / Vite 构建问题。
6. 再次执行 test + build。

### Backend

1. 安装 `backend/requirements.txt`。
2. 执行 Runtime Query RBAC、RBAC Matrix、HTTP RBAC、API Contract 测试。
3. 修复真实失败。
4. 执行完整 `pytest -q`。
5. 记录真实结果。

### CI

当前 `.github/workflows/ci.yml` 仅保留 `workflow_dispatch`，自动 push / pull_request 已暂停。先完成本地质量闭环，再评估恢复自动 CI。

## 3. 完成标准

- Frontend test 实际执行并记录结果。
- Frontend build 实际执行并记录结果。
- Backend pytest 实际执行并记录结果。
- HTTP 401 / 404、Owner / Admin Scope、Filter 有执行证据。
- 不把未执行结果标记为通过。
- 不提交 `node_modules`、`dist`、`coverage`、临时日志。

## 4. 文档规则

Task 07 完成后提交 `docs/39` 完成记录和 `docs/40` 下一阶段规划；若环境仍阻塞，完成记录必须准确写明阻塞原因和未验证项目。
