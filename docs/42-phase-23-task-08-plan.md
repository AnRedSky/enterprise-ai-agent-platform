# 42 - Phase 23 Task 08 下一阶段规划

## 1. 目标

验证 Task 07 的 Vitest mock 修复，并继续完成 Frontend build 与 Backend RBAC 实测闭环。

## 2. 执行步骤

1. `cd frontend && npm test`
2. `cd frontend && npm run build`
3. `cd backend && pytest -q`
4. `pytest -q tests/test_runtime_http_rbac.py`
5. `pytest -q tests/test_runtime_rbac_matrix.py`
6. 如有失败，只修复真实失败项并补充回归测试。
7. 所有结果记录后，再评估 Phase 23 是否达到验收条件。

## 3. 提交规则

Task 08 完成时提交：

- `docs/43` 完成记录
- `docs/44` 下一阶段规划
- 对应代码和测试

在测试全部通过前，不恢复 CI 自动质量门禁，不宣称 Phase 23 完成。
