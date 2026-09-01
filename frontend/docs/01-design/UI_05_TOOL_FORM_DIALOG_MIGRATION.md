# UI-05 Tool Dialog / Confirm 统一迁移

## 状态

进行中：完成 ToolWorkbench 第一批 UI-05 迁移，建立公共 `ConfirmDialog` 并接入高风险工具操作；第二批已完成创建 Dialog 的校验、提交和失败保留语义。

## 目标

在不复制业务规则、不新增 API Contract 的前提下，统一表单、Dialog、Drawer 与危险操作确认模式。每次只迁移一个核心页面。

## 本次范围

- 保留公共 `src/components/ui/ConfirmDialog.vue` 作为危险操作确认入口。
- ToolWorkbench 的“停用工具”和“解绑工具”入口继续经过公共确认组件。
- ToolWorkbench 创建 Dialog 增加本地输入校验：名称必填；`input_schema` 必须为 JSON 对象。
- 创建请求只在校验通过后提交；成功才关闭并重置表单；API 失败保留用户输入。
- Dialog 使用视口约束宽度，避免小屏幕横向溢出。

## 交互契约

| 场景 | 处理 |
| --- | --- |
| 停用已启用工具 | 危险确认；确认后调用已有 disable API 并刷新列表 |
| 启用已停用工具 | 普通确认；确认后调用已有 enable API 并刷新列表 |
| 解绑工具 | 危险确认；必须已有智能体选择后才能执行 |
| 创建工具名称为空 | 阻止提交并提示“请输入工具名称。” |
| `input_schema` 非 JSON 对象 | 阻止提交并提示格式错误 |
| 创建请求处理中 | 创建按钮显示 loading，避免重复提交 |
| 创建成功 | 关闭 Dialog、重置表单、刷新工具列表并提示成功 |
| 创建失败 | 不关闭 Dialog，保留输入，展示通用用户错误 |

## Contract / 安全边界

本次没有新增或修改后端 API。继续复用现有 `createTool`、`enableTool`、`disableTool`、`unbindTool`；`ToolCreatePayload.input_schema` 仍按正式 API 类型使用 `Record<string, unknown>`。权限仍由后端最终裁决；前端仅根据既有 admin 角色控制入口展示。

## 测试

更新 `tests/views/Tools.test.ts`，覆盖：

1. 危险操作进入公共 `ConfirmDialog`；
2. 空名称阻止 API 请求；
3. 非对象 JSON 阻止 API 请求；
4. 成功提交时规范化字符串字段并关闭/重置；
5. API 失败时保留表单输入。

本轮远端环境未执行 Node/Vitest，因此不能将 targeted/full test 标记为已通过。用户本地建议命令：

```powershell
cd frontend
npm run test:unit -- --run tests/views/Tools.test.ts
npm run test:unit -- --run tests/components/ConfirmDialog.test.ts tests/views/Tools.test.ts
npm test
npm run build
npm run test:gate
npm run test:final
```

## 后续

完成用户本地 targeted/full 门禁后，再选择第二个核心页面迁移；避免新增平行 Dialog/Confirm 组件。
