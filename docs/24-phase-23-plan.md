# 24 - Phase 23 下一阶段规划

## 1. 目标

在 Phase 22 Runtime Management 基础上完成测试闭环、前端质量保障、CI 恢复评估，并为后续 Runtime Observability / Operations 能力提供稳定基线。

## 2. 优先级

### P0 - 测试与质量闭环

1. 执行 `backend/tests/test_runtime_rbac_matrix.py`。
2. 执行 Runtime Response Contract Tests。
3. 增加 API 层真实 HTTP RBAC 测试，验证 401 / 403 / 404。
4. 覆盖 Execution Filter、Audit Filter、Pagination。
5. 验证跨 Owner 资源不存在性不泄露。

### P1 - Vue 测试

1. 建立 Vue Test 工具链。
2. Runtime List 测试。
3. Timeline 测试。
4. Audit Log 测试。
5. Empty / Loading / Error 状态测试。
6. API 失败场景测试。

### P1 - CI

1. 保持当前 CI 临时暂停策略，避免阻塞开发。
2. 汇总历史 CI 失败日志。
3. 修复 Python / Node 依赖、测试环境和缓存配置。
4. 在本地可重复通过后恢复 GitHub Actions。
5. 恢复后要求 backend test、frontend build/typecheck 全部通过。

### P2 - Runtime Operations

1. 完善 Runtime Dashboard。
2. 增加 Execution 状态统计。
3. 增加失败率、耗时等基础指标。
4. 增加 Audit Log 更完整筛选条件。
5. 增加 Trace / Request / Session 联动查询。

## 3. 文档要求

每次 Phase 23 功能完成时，同时提交对应下一阶段规划文档；禁止出现代码已经完成但下一阶段计划未进入仓库的情况。

## 4. 完成标准

- Backend Runtime 测试可重复执行。
- RBAC / Filter / Audit / Pagination 验收通过。
- Frontend Runtime 核心组件具备自动化测试。
- CI 恢复后主分支质量门禁稳定。
- 所有提交仅包含项目代码、测试、配置和必要开发文档。
