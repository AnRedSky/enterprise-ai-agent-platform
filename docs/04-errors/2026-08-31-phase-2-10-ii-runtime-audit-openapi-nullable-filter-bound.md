# Phase 2.10-II Runtime Audit 查询 OpenAPI nullable 过滤边界断言失败

## 1. 发生时间

2026-08-31

## 2. 所属任务

Phase 2.10-II / II-07 Runtime Audit Query 运维主体过滤、动作与结果组合过滤及查询契约硬化。

## 3. 现象

开发者本地执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\21_runtime_audit_action_outcome_hardening_gate.ps1
```

Migration/head 与 migration upgrade 正常完成；9 个 Runtime Audit Unit/API Contract 测试中 7 个通过，以下 2 个失败：

- `test_runtime_audit_query_exposes_filter_bounds`
- `test_runtime_audit_query_exposes_optional_actor_filter`

失败均为 `KeyError: 'maxLength'`，断言直接从 OpenAPI parameter schema 根节点读取 `maxLength`。

## 4. 根因

Runtime Audit 的 `action` 与 `actor` 均属于可选字符串查询参数。OpenAPI 生成器在 nullable 参数场景下允许将字符串约束放入 `anyOf` 的字符串分支，而不是保证 `maxLength` 始终位于 parameter schema 根节点。

原测试把 OpenAPI 内部序列化结构误当成稳定的契约结构，导致即使生产参数仍正确声明长度边界，也可能因为 schema 表示形式变化而失败。

该问题属于 API Contract 测试断言方式过窄，不是 Runtime Audit 查询业务过滤逻辑缺失。

## 5. 修复

对 Runtime Audit API Contract 测试增加统一语义读取逻辑：

1. 优先读取 schema 根节点的 `maxLength`；
2. 若根节点没有 `maxLength`，继续检查 `anyOf` 中 `type=string` 的分支；
3. 找不到字符串长度约束时显式抛出断言错误并打印实际 schema。

同时将 `action`、`resource_type`、`resource_id`、`outcome`、`actor` 五个 operational filter 的边界断言统一使用该逻辑，避免同类 OpenAPI nullable 表示再次产生不一致测试行为。

## 6. 验证要求

修复后必须由开发者本地重新执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\21_runtime_audit_action_outcome_hardening_gate.ps1
```

随后继续执行当前主线要求的：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\22_runtime_audit_query_contract_hardening_gate.ps1
```

Gate 仍必须保持服务启动边界：只允许检查依赖服务状态，不得自动创建、启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis；测试身份、ID 和业务事实必须自动生成。

## 7. 验收状态

代码修复已提交到 `main`，但本轮环境无法直接访问开发者本地 PostgreSQL / Runtime 环境，因此不宣称本地 Gate 已通过。最终验收以开发者重新执行 Gate 的实际输出为准。
