# UI-05 Tool Dialog / Confirm 统一迁移

## 状态

进行中：完成 ToolWorkbench 第一批 UI-05 迁移，建立公共 `ConfirmDialog` 并接入高风险工具操作；普通创建/绑定/执行 Dialog 暂保持现有 Element Plus 结构，下一批逐步收敛。

## 目标

在不复制业务规则、不新增 API Contract 的前提下，统一表单、Dialog、Drawer 与危险操作确认模式。每次只迁移一个核心页面。

## 本次范围

- 新增 `src/components/ui/ConfirmDialog.vue`。
- ToolWorkbench 的“停用工具”和“解绑工具”入口先经过公共确认组件。
- 确认组件只负责展示、loading 和事件派发，不包含 Tool 领域规则。
- 保留创建、绑定、执行三个现有 Dialog，避免一次性重构造成行为漂移。

## 交互契约

| 场景 | 处理 |
| --- | --- |
| 停用已启用工具 | 危险确认；确认后调用已有 disable API 并刷新列表 |
| 启用已停用工具 | 普通确认；确认后调用已有 enable API 并刷新列表 |
| 解绑工具 | 危险确认；必须已有智能体选择后才能执行 |
| 请求处理中 | 禁止关闭确认操作，确认按钮显示 loading |
| API 失败 | 使用既有 `getToolUserError`，不展示原始异常 |

## Contract / 安全边界

本次没有新增或修改后端 API。继续复用现有 `enableTool`、`disableTool`、`unbindTool`，权限仍由后端最终裁决；前端仅根据既有 admin 角色控制入口展示。

## 测试

新增：`tests/components/ConfirmDialog.test.ts`，覆盖：

1. 标题、说明和动作文案；
2. confirm/cancel 事件；
3. loading 时阻止取消。

更新：`tests/views/Tools.test.ts`，验证危险工具操作进入公共 `ConfirmDialog`。

本轮远端环境未执行 Node/Vitest，因此不能将 targeted/full test 标记为已通过。用户本地验证命令：

```powershell
cd frontend
npm run test:unit -- --run tests/components/ConfirmDialog.test.ts tests/views/Tools.test.ts
npm test
npm run build
npm run test:gate
npm run test:final
```

## 后续

继续以 ToolWorkbench 为 UI-05 样板，下一步统一其创建 Dialog 的表单提交/校验/关闭语义；确认测试通过后再迁移第二个核心页面。避免新增平行 Dialog/Confirm 组件。
