# Phase 2.7-A — Advanced Workflow Orchestration / Conditional Branching Contract

> 状态：**Contract 已冻结，首个实现单元为 Conditional Branching。**
> 基线：`main`，2026-08-27。
> 范围：只定义确定性条件边与 Resume/Runtime frontier 语义；人工节点、Saga、Policy DSL、MQ/Event Bus 不属于本交付单元。

## 1. 目标

在现有 Workflow DAG、Checkpoint、Resume、Branch、Join 基础上增加受控 Conditional Branching，使 Workflow 可以根据当前 Runtime state 选择后继边，同时保持：

- tenant / RBAC 边界不变；
- Workflow Version immutable；
- Checkpoint 仍是持久化事实；
- Planner 只负责纯内存规划；
- Runtime 不复制条件解析规则；
- Resume 必须重新基于持久化事实计算 frontier。

## 2. Edge Contract

Edge 最少包含：

```json
{
  "source": "node-a",
  "target": "node-b"
}
```

条件边扩展为：

```json
{
  "source": "node-a",
  "target": "node-b",
  "condition": {
    "op": "eq",
    "path": "result.status",
    "value": "approved"
  }
}
```

允许字段：`source`、`target`、`condition`、`default`。

- `source` / `target` 必须是已存在 Node ID；
- `condition` 与 `default` 不能同时存在；
- 无 `condition` 且无 `default` 的 edge 保持无条件边兼容语义；
- `default=true` 表示仅当同一 source 的其他条件边全部未命中时才选择该边；
- 同一 source 最多一个 default edge；
- 重复 `source -> target` edge 仍然拒绝，避免幂等与审计歧义。

## 3. Condition DSL

Condition 必须是有限 JSON 对象，只允许纯计算：

```text
eq / ne / gt / gte / lt / lte
in / contains
and / or / not
```

路径读取采用点号路径，例如 `result.status`、`metadata.score`。根状态只能来自当前 Runtime `state_data`。

禁止：

- Python / JavaScript / Jinja / 模板代码执行；
- 函数调用；
- 网络、数据库、文件或 Provider 调用；
- 动态属性访问；
- 隐式字符串到数字、布尔等危险类型转换。

表达式必须限制最大深度与节点数量，超限直接拒绝。

## 4. 类型与比较

- `eq / ne` 使用严格 JSON 类型比较；`true` 不等于 `1`；
- `gt / gte / lt / lte` 仅允许双方均为 number；
- `in` 左值必须严格匹配数组中的一个元素；
- `contains` 仅允许字符串包含字符串，或数组包含严格相等元素；
- 缺失 path 视为“未提供”，不能通过隐式 null 转换改变比较结果；
- `and / or` 使用短路求值；`not` 只接受单一 condition。

## 5. 多出边选择

同一 source 的 outgoing edges 按 Definition 中出现顺序确定性评估：

1. 先评估普通 condition edges；
2. 所有命中的 condition edges 均进入 frontier，保持 Definition 顺序；
3. 如果没有任何 condition 命中，则选择 default edge（如果存在）；
4. 如果没有命中且没有 default，则该 source 不产生后继 frontier；
5. 无条件 edge 与 condition/default edge 混用属于非法 Definition，避免隐式多路语义。

因此 Conditional Branching 首版允许显式并行 frontier，但不允许通过条件表达式制造非确定性执行。

## 6. Resume Contract

Resume 必须：

```text
Source / Checkpoint persisted facts
        ↓
Workflow Version immutable validation
        ↓
Condition evaluation against current state_data
        ↓
selected frontier
        ↓
existing Branch / Join planner
```

不得使用 Resume 创建时缓存的 frontier。Definition 或 Workflow Version 发生漂移时拒绝恢复。

未命中的分支不产生 completed NodeExecution，也不得伪装为 Join predecessor 已完成。

## 7. Join Contract

- Join readiness 只由实际执行完成的 predecessor facts 决定；
- 未命中条件边不是 completed fact；
- Join 不自行执行条件判断；
- Join state merge 继续复用现有 `WorkflowDagBranchStateMergeService`；
- 条件决策摘要可以进入 Trace，但不得写入 Secret、Prompt 或完整业务 payload。

## 8. 拓扑与安全

继续复用现有 DAG Contract 的：

- 单 root；
- 无 self-loop；
- 无重复 edge；
- 无未知 Node 引用；
- 无孤立 Node；
- 无循环图。

新增条件约束：

- condition schema 非法直接拒绝发布；
- condition 最大深度 / 节点数固定上限；
- default edge 最多一个；
- condition/default 与无条件 edge 不允许产生歧义；
- 同一 source 的边评估顺序必须稳定。

## 9. 实施顺序

```text
Contract
  ↓
Condition evaluator unit tests
  ↓
DAG Contract extension
  ↓
Conditional frontier planner
  ↓
Runtime integration
  ↓
Real API acceptance
  ↓
Phase / Acceptance / Status / Error update
  ↓
main
```

## 10. 禁止范围

当前不实现：

- 人工审批节点；
- Saga / compensation；
- 通用 Policy DSL；
- 任意代码表达式；
- MQ / Kafka / Event Bus；
- 跨 Workflow Version 恢复；
- 第二套 DAG Planner / Runtime / State Merge。
