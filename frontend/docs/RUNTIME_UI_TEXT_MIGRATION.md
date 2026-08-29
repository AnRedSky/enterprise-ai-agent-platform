# Runtime 页面中文文案统一记录

## 目标

将运行中心面向普通用户的界面统一为通俗、明确的中文，同时保留运行记录 ID、链路 ID、请求 ID、会话 ID、节点 ID、事件类型和错误代码等诊断字段的原始值。

## 本次范围

- 运行记录列表、状态筛选、空状态和错误提示。
- 运行记录详情抽屉。
- 运行时间线、检索信息和工作流运行链路。
- Execution、Status、Agent、Trace、Started、Request、Session、Model、Latency 等用户可见字段统一为中文。
- Timeline Event、Workflow Trace Event、Error Code、Node 等界面标签统一为中文。

## 保留原则

技术标识不是自然语言文案，不进行翻译或改写：运行记录 ID、链路 ID、请求 ID、会话 ID、节点 ID、事件类型、错误代码以及 JSON 数据保持后端原始值，便于日志检索、故障排查和跨系统关联。

## 实现原则

1. 不修改 Runtime API 请求和响应结构。
2. 用户可理解的标题、按钮、字段名、空状态和错误提示使用中文。
3. 后端枚举和事件类型只有在存在明确的展示映射时才转换，避免凭经验臆造业务含义。
4. 新增用户可见英文术语必须在代码评审中说明，并同步更新本规范记录。
5. 定向测试覆盖中文文案和技术标识保留规则。

## 验证要求

Runtime 页面修改后依次执行：

1. `npm test -- tests/views/Runtime.test.ts`
2. `npm test`
3. `npm run build`
4. `npm run test:gate`

本次修改不得改变 Runtime API 调用参数、分页行为或详情加载行为。
