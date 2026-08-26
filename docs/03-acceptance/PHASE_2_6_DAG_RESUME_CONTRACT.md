# Phase 2.6 — DAG Resume Runtime Contract

## 状态

**Contract 已冻结；Planner / Runtime DAG 实现尚未进入。**

本文件只冻结第一版 DAG Resume 的图结构与安全边界，不改变当前已验收的顺序 Resume 行为。

## 1. Edge Contract

Workflow Definition 进入 DAG Resume 图模式时，`edges` 必须为非空数组，每条 Edge 只能包含：

```json
{
  "source": "node-a",
  "target": "node-b"
}
```

规则：

- `source` / `target` 必须是非空字符串；
- 两端 Node 必须存在于同一 Definition 的 `nodes`；
- 不允许 self-loop；
- 不允许重复的有向边；
- 不允许额外字段；第一版不接受条件表达式、权重、优先级或运行时元数据；
- `nodes` 的 `id` 必须唯一；
- DAG 图模式不接受空 `edges`；空 `edges` 继续保留给现有顺序 Runtime；
- 孤立 Node 不属于第一版 DAG 图模式；
- 图必须无环。

## 2. Resume 完成事实

Resume frontier 不得从 Definition 单独推断“已经执行过什么”。唯一完成事实仍来自 Source Execution 持久化的 Node Execution / Checkpoint。

Checkpoint 只提供已验证的恢复状态快照；它不改变 Source Execution 的终态，也不绕过 Worker ownership。

## 3. Resume frontier

第一版 DAG Planner 后续必须从“Checkpoint 对应 Node 已完成”这一持久化事实计算后继 frontier：

- 已完成 Node 本身不再次进入 frontier；
- 直接后继只有在其所有必要前置完成事实满足时才能进入可执行 frontier；
- 多入边节点不得因为任意一条入边完成就被错误执行；
- frontier 顺序必须确定性；
- frontier 计算不得读取或修改数据库；
- Planner 不拥有 Worker、Execution 或事务状态。

## 4. 分支、汇聚与条件

第一版 Contract 允许普通 DAG 拓扑，因此允许一个 Node 有多个出边，也允许目标 Node 存在多个入边。

但第一版 Runtime **不承诺 Worker 内并行执行**。在并行 Runtime 尚未冻结前，frontier 必须保持确定性顺序消费，不得通过顺序循环伪装“并行已支持”。

第一版不支持条件边。需要条件执行时，必须先新增明确的 Contract 与测试，不得在 `source/target` Edge 中塞入未定义字段。

## 5. State 恢复

Checkpoint `state_data` 是 Resume 的初始 Runtime 输入事实。

第一版不定义多个并行分支之间的自动 state merge 规则；因此在正式 merge Contract 冻结前，Planner 不得自行覆盖、拼接或猜测多个分支输出。

## 6. 失败边界

某个 Resume frontier Node 失败时：

- Resume Execution 进入 `failed`；
- 已成功提交的 Node Execution / Checkpoint 保持事实；
- Source Execution 不被复活；
- 不创建虚假的完成 Checkpoint；
- 后续 Resume 必须重新以持久化 Checkpoint 事实作为输入；
- Worker ownership / lease fencing 仍由现有 Worker 路径负责。

## 7. 幂等与 Version

相同 Source Execution、Checkpoint sequence 与相同 Workflow Version Definition 必须生成稳定的 Planner 输入。

Workflow Version 发生漂移时拒绝恢复；Resume 不读取新的 published Version 替换原 Source Version。

现有 `tenant_id + idempotency_key` 与 `resume_of_execution_id + resume_checkpoint_sequence` 不变量继续有效，本 Contract 不修改既有持久化模型。

## 8. 拓扑安全

第一版 DAG Contract 必须拒绝：

- Node ID 重复；
- Edge source / target 缺失；
- Edge 引用不存在 Node；
- 重复 Edge；
- self-loop；
- 孤立 Node；
- 环路；
- 未定义 Edge 字段。

多根 DAG 在图结构层面允许存在；是否可以作为一个可恢复 Workflow 执行，需要由后续 Runtime 起点 Contract 单独冻结。

## 9. Runtime 接口

Planner 只负责纯内存计算并输出确定性的 Resume Plan。它不：

- 创建 Execution；
- 修改 Node / Execution 状态；
- 获取 Worker lease；
- 操作数据库事务；
- 直接调用 WorkflowRuntime；
- 自动恢复 failed Execution。

Runtime 集成阶段必须由 Worker 将经过 Source / Checkpoint / Version 重新校验的 Plan 交给 Runtime。

## 10. 实施顺序

```text
Contract
  ↓
DAG Contract Validator + Planner 单元测试
  ↓
DAG Planner 实现
  ↓
Runtime Integration / failure boundary
  ↓
真实 PostgreSQL + 独立 Worker DAG Acceptance
```

本 Contract 对应 GitHub Issue #49；在 DAG Planner / Runtime Acceptance 未完成前，不关闭 Phase 2.6。
