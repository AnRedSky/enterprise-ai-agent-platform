# UI-04 页面状态统一规范

## 1. 目标

统一前端页面的 Loading / Empty / Error / Permission / Success 状态，避免各业务页面自行定义状态视觉和恢复操作。

## 2. 公共组件

`src/components/ui/StatePanel.vue` 是 UI-04 首个公共状态组件。

```text
loading     数据正在加载，可等待
empty       请求成功但没有业务数据
error       请求失败，允许提供重试操作
permission  当前用户没有执行该操作的权限
success     操作完成，需要给出明确结果
```

组件只负责状态表达和用户恢复入口，不承载业务权限判断、API 请求或业务状态机。

## 3. 状态语义

### Loading

- 不与 Empty 同时展示；
- 首屏请求使用明确的加载语义；
- 重试时保留用户上下文，不清空已有有效数据。

### Empty

- 仅表示请求成功且结果为空；
- 必须给出下一步建议；
- 不得使用 Error 文案代替 Empty。

### Error

- 请求失败与业务空数据严格区分；
- 对用户显示可理解的错误信息；
- 可恢复请求提供“重试”；
- 不直接暴露后端堆栈、SQL、内部地址或敏感信息。

### Permission

- 无权限时不进入业务操作流程；
- 明确说明缺少的访问/操作权限；
- 不通过隐藏按钮制造“页面正常但操作失败”的体验。

### Success

- 写操作完成后给出明确反馈；
- 成功消息不能替代页面数据刷新；
- 状态变化应重新同步服务端数据。

## 4. 页面集成原则

公共 `StatePanel` 用于页面级和局部业务状态；Element Plus `v-loading` 继续用于表格/容器级加载遮罩，两者不互相替代。

业务页面不得复制 `StatePanel` 的视觉 CSS。颜色、间距、圆角必须使用 Design Tokens。

## 5. 首轮落地

本轮完成：

- 新增 `StatePanel.vue`；
- 覆盖五种标准状态；
- 提供可恢复 Action；
- 支持 reduced-motion；
- 注册 Element Plus `ElIcon`；
- 新增 `tests/components/StatePanel.test.ts`。

下一轮仅选择一个核心页面，将其现有 Loading / Empty / Error / Permission / Success 迁移到该组件；不批量改造。

## 6. 测试

```powershell
cd frontend
npm test -- tests/components/StatePanel.test.ts
npm test
npm run build
npm run test:gate
npm run test:final
```

当前远端开发环境未实际运行 Node/Vitest/build，因此测试结果不得标记为通过。
