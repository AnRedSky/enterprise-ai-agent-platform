# Agent 页面 UI 文本迁移记录

## 本轮目标

将智能体工作台的用户可见英文统一迁移为通俗、明确的中文，同时保持 API Contract、后端状态枚举、模型标识和运行过程技术 ID 不变。

## 已完成

- 页面标题：`Agent 工作台` → `智能体工作台`
- 页面说明：改为中文业务表达
- 操作按钮：`创建 Agent` → `创建智能体`；`调试 Chat` → `对话调试`；`发布最新` → `发布最新版本`
- 生命周期标识：`Published` → `已发布`
- 表单字段：`System Prompt` → `系统提示词`
- 版本弹窗：`Agent Versions` → `智能体版本`
- 对话角色：`Agent` → `智能体`
- 运行标识：`Request`、`Trace`、`Session`、`Execution` → `请求 ID`、`链路追踪 ID`、`会话 ID`、`执行 ID`
- 错误提示和成功提示统一为中文，并增加必要的下一步说明
- 空状态统一使用“暂无智能体，请先创建一个。”

## 明确保留的技术值

以下内容属于代码协议或排障信息，不做中文化：

- `published`、`archived`、`streaming` 等后端/运行状态枚举
- `agent_id`、`model_id` 等 API 字段
- `request_id`、`trace_id`、`session_id`、`execution_id` 的实际值
- `mock-model` 等模型标识

## 测试约束

`Agents.test.ts` 增加用户可见文本回归测试：验证核心中文术语存在，并反向断言旧的 `Agent`、`Published`、`System Prompt`、`Chat` 等界面英文不再出现。

## 后续迁移

继续按同一规则处理 Workflow、Runtime、知识库、工具、组织、审计、模型服务等页面。技术字段只在 UI 标签层中文化，不修改接口协议和后端枚举。
