# Agent 当前生效版本能力补全

## 目标

在不改变现有智能体工作台信息架构的前提下，直接使用后端已经存在的 `GET /agents/{agent_id}/published-version` Contract，让用户可以查看当前真正生效的版本配置。

## 为什么先做这个切片

Agent 是当前长期任务 P0 的第一项，后端已有 Agent、Version、Publish 和 published-version API。相比等待尚未完成 Runtime Acceptance 的 2.10-I 新能力，本切片直接消费稳定 Contract，能够降低前后端错位风险。

## 实现

- Agent 列表的已发布智能体增加“查看生效版本”。
- 点击后调用正式 `getPublishedVersion` API，不从列表字段推断版本详情。
- 展示版本、模型、系统提示词、知识库数量、检索数量、创建时间和版本标识。
- API 失败只显示中文业务提示，不展示后端异常原文。
- 技术版本标识保留，方便排障。

## 测试

新增页面回归验证：

- 调用参数必须为当前 Agent ID；
- 使用后端返回的 `knowledge_config`；
- 页面显示“当前生效版本”和“版本标识”；
- 后端异常不得直接进入用户提示。

## 验收边界

本切片不提前实现 Notification、Provider fallback、Alert Scheduler 等 2.10-I 未完成 Runtime Acceptance 的前端能力，也不改变 Agent API Contract。

## 后续

下一 Agent 切片继续检查已稳定 Contract 中的 Knowledge / Tool / Runtime 关联；完成 Agent 后进入 Workflow → Runtime 主链路。
