# 003 Circuit Breaker 新建状态计数初始化缺陷

## 发生阶段

Phase 1.5-G Circuit Breaker Real API。

## 实际错误

Circuit Breaker 首次 `record_failure()` 创建 `WorkflowCircuitState` 后，在 SQLAlchemy `flush` 前读取 `failure_count`，在测试 mock / 真实 ORM 行为下可能得到 `None`，导致：

```text
TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'
```

该问题进一步导致 Real API bootstrap 期望 `503 CIRCUIT_OPEN` 时实际得到 `500 Internal Server Error`。

## 根因

业务代码依赖数据库 column default / ORM flush 后默认值，却在 flush 前读取计数属性。对于新增 ORM 对象，数据库默认值尚未回填，因此不能假设 Python 对象属性已经是整数。

## 影响

1. 首次 failure 无法正常建立 Circuit State。
2. Real API fixture 无法建立 OPEN 场景。
3. 业务异常可能进入错误的 500 路径，破坏治理错误码契约。
4. 如果异常后继续复用同一数据库事务，还可能触发 PostgreSQL `InFailedSQLTransactionError`。

## 修复方案

1. 新建 Circuit State 时显式初始化 `failure_count`、`success_count`、`state` 等业务状态字段。
2. 在首次 failure 与 `before_call` 场景增加回归测试。
3. Real API 使用真实 PostgreSQL + HTTP fixture 验证状态机，而不是只依赖 mock。
4. 事务异常必须正确 rollback / 进入失败恢复路径，不能在 aborted transaction 中继续查询或更新。

## 预防措施

- ORM 业务逻辑不能把数据库 server default 当作 flush 前的 Python 对象默认值。
- 所有状态机计数器必须在 domain object 创建时显式给出初始值。
- 新增数据库状态字段后，同时覆盖首次创建、首次失败、状态转换和真实 API 场景。
- Real API bootstrap 失败时必须优先检查原始数据库异常，不能仅根据最终 HTTP 状态判断业务逻辑错误。

## 验证要求

至少覆盖：

```text
新建 State → failure_count = 0
首次 failure → 正确递增
达到 threshold → OPEN
OPEN → Fast-Fail 503 / CIRCUIT_OPEN
OPEN → HALF_OPEN
probe success → CLOSED
probe failure → OPEN
```

## 实际验证结果

项目当前 `PROJECT_STATUS.md` 已记录 Phase 1.5-G 最终本地验收结果；本错误记录本身不重复预填测试结果。
