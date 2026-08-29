# 开发准则执行补充：本地服务生命周期与数据库迁移 Gate

> 本文件是 `docs/01-governance/DEVELOPMENT.md` 的执行补充，重点固化本地真实验收、服务生命周期与 Alembic 拓扑检查规则。若与唯一开发准则冲突，以 `DEVELOPMENT.md` 为准。

## 1. 服务生命周期规则

Real API / Runtime Acceptance Gate 默认**不得自动启动、停止或重启任何开发服务**。

Gate 必须：

1. 自动检查 API / Scheduler / Worker 等前置服务是否已经运行；
2. 服务缺失时明确输出服务名称、失败原因和人工启动命令，然后以非零退出码结束；
3. 不修改开发者已有进程；
4. 不通过 `Start-Process`、后台 shell、Docker Compose 或其他方式隐式拉起服务；
5. 测试身份、租户、规则、Policy、Destination、Subscription 等业务数据必须由测试代码自动生成和清理，不允许要求开发者手工填写 UUID、Token 或业务参数。

服务启动命令属于 Gate 的前置说明，而不是 Gate 的自动执行动作。

## 2. Migration Gate 规则

涉及数据库结构的任务必须至少验证：

```text
alembic heads
    ↓
alembic upgrade heads
    ↓
alembic current
    ↓
对应 migration topology unit test
```

发现多个并行 revision 时，必须明确判断它们属于：

- 有意保留的独立 Head；或
- 必须在后续 migration 汇合的功能分支。

如果后续 migration 依赖并行分支中的表或列，不得仅依赖开发者当前数据库状态；必须在 Alembic graph 中显式表达依赖关系，并增加 topology test。

## 3. Migration 与业务代码顺序

业务代码不得假设某张表“通常已经存在”。凡是代码直接查询、创建外键或写入某个 migration 新增的表，该 migration 必须在真实 PostgreSQL 上先完成。

尤其是以下情况必须建立 topology test：

- 多个同级 migration 分支；
- `down_revision` 使用 tuple；
- `depends_on`；
- 后续 migration 创建跨分支 Foreign Key；
- 后续 migration 修改前置分支创建的字段。

## 4. 测试结果真实性

自动化脚本只能报告实际执行结果：

```text
未执行 = NOT EXECUTED
前置条件失败 = BLOCKED
测试执行失败 = FAILED
测试实际成功 = PASSED
```

文档、提交信息和项目状态不得把未执行的 Real PostgreSQL / Runtime Acceptance 描述为已通过。

## 5. Runtime Acceptance 最小链路

涉及告警通知生命周期时，Real Acceptance 至少覆盖：

```text
Alert Evaluation
→ Firing / Recovery
→ Notification Policy
→ Grouping / Dedup / Cooldown
→ Provider Routing
→ Delivery Worker
→ Delivery Outcome
→ Retry / Fallback / DLQ
→ SLO / Metrics
→ Operational Audit
```

其中 Scheduler / Worker 的存在性必须作为真实后台生命周期前置条件检查；测试不得用 Mock Worker 代替需要验证的后台运行链路。

## 6. 提交前检查

数据库相关修复提交前必须完成：

- migration 文件与 topology test 同步；
- 旧错误记录写入 `docs/04-errors/`；
- 对应 Runtime / Real API Gate 已更新；
- 没有通过测试代码复制生产算法；
- 没有新增与现有 Service / Provider / Repository 平行的重复实现；
- 本地执行结果如实记录，未执行项不得写成通过。
