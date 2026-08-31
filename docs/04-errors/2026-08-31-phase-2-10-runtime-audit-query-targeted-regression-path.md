# Phase 2.10-II Runtime Audit Query targeted regression 路径失效

## 1. 现象

开发者本地执行 `14_runtime_audit_query_unit_gate.ps1` 时，Runtime Audit Query Unit / API Contract 已通过，但 `[3/4] Backend targeted regression` 失败：

```text
ERROR: file or directory not found: tests/unit/test_runtime_operations.py
Runtime targeted regression failed.
```

## 2. 根因

Runtime Operations 已按领域职责拆分，当前正式的 Runtime Audit Query 单元测试位于：

`backend/tests/unit/test_runtime_operations_audit_query.py`

仓库中不存在旧的聚合测试路径：

`backend/tests/unit/test_runtime_operations.py`

因此 Gate 脚本仍引用历史路径，属于测试编排与当前模块结构不同步，而不是生产代码或 Runtime Audit Query 查询逻辑错误。

## 3. 修复

将 `backend/scripts/test/phase-2.10/14_runtime_audit_query_unit_gate.ps1` 的 targeted regression 改为当前有效测试入口：

- `tests/unit/test_runtime_operations_audit_query.py`
- `tests/api_contract/test_api_runtime_endpoints.py`

这样继续覆盖 Runtime Audit Query 查询规则、分页/过滤边界以及 Runtime API 路由总体装配，同时不恢复已删除的旧测试模块。

## 4. 设计约束

- 不创建兼容旧路径的测试垫片；
- 不复制 Runtime Operations 测试实现；
- 不修改生产查询算法；
- Backend Gate 不启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis；
- Real Acceptance 继续使用自动生成的测试身份和业务事实。

## 5. 后续验证

修复后的 Gate 应重新执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\14_runtime_audit_query_unit_gate.ps1
```

只有 Unit / API Contract / targeted regression 均通过后，才继续执行 `15_runtime_audit_query_real_gate.ps1`，并以开发者本地实际结果决定 II-06 第一切片是否收口。
