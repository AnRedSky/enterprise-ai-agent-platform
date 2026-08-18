# Phase 24 Task 02：Backend Runtime / Tool / Memory 验证计划

## 目标

在测试收集阶段问题修复后，进入真实 Backend 功能验证，不再通过跳过、xfail 或修改断言规避失败。

## 执行顺序

1. Backend 全量 pytest
2. Runtime API Contract
3. Runtime HTTP RBAC
4. Runtime Query RBAC
5. RBAC Matrix
6. Tool Runtime
7. Tool HTTP Security
8. Tool Runtime E2E / Failure / Security
9. Memory Context / Governance / Service
10. Model Gateway
11. Observability

## 交付标准

- 测试必须能正常 collection。
- 失败必须定位到实际代码、配置或环境依赖。
- 代码修复后重新执行受影响测试，再执行全量回归。
- 每轮完成时同时提交当前完成记录和下一阶段规划文档。

## 当前优先级

P0：解决测试环境依赖与剩余 collection errors。
P1：Runtime/RBAC 全部通过。
P1：Tool 安全与 E2E 全部通过。
P1：Memory / Model Gateway / Observability 回归通过。
P2：恢复 CI 前进行本地全量验收。
