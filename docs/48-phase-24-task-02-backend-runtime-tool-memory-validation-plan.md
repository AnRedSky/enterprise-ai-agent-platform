# Phase 24 / Task 02：Backend Runtime / Tool / Memory 验证规划

## 1. 进入条件

Phase 24 / Task 01 已完成 pytest 导入环境修复，但最终测试结果仍以开发环境人工执行结果为准。

## 2. 下一阶段目标

在 Backend 基础 pytest 能够正常收集和执行后，按以下顺序验证并推进：

1. Runtime API Contract
2. Runtime HTTP RBAC
3. Runtime Query RBAC
4. RBAC Matrix
5. Tool Runtime 单元与安全测试
6. Tool Runtime E2E
7. Memory Context / Governance / Service
8. Model Gateway
9. Observability

## 3. 推进原则

- 先验证已有实现，再修改缺陷；
- 不以测试收集成功替代测试通过；
- 不使用 `skip`、`xfail` 或降低断言绕过失败；
- 每个完成任务必须同步提交完成记录和下一阶段规划；
- 所有开发基于最新 `main`。

## 4. 人工验证命令

```bash
cd backend
pytest -q
pytest -q tests/test_runtime_http_rbac.py
pytest -q tests/test_runtime_rbac_matrix.py
```

若上述测试通过，再按本规划逐组执行 Tool、Memory、Model Gateway、Observability 测试。

## 5. 交付目标

完成 Backend 质量验证闭环，并据真实测试结果修复剩余实现问题；随后进入 Tool / Memory / Observability 的功能完整性验收与未完成开发任务。
