# UI-04 KnowledgeWorkbench 状态迁移

## 范围

本轮仅迁移 `KnowledgeWorkbench.vue` 的页面级 Loading / Empty / Error / Permission / Success，不修改 Knowledge API Contract，不迁移 Tool 页面。

## 状态映射

- Loading：知识库首屏加载期间使用 `StatePanel.loading`。
- Empty：查询成功且知识库为空，使用 `StatePanel.empty`，提供创建入口。
- Error：知识库查询失败，使用 `StatePanel.error` 并提供 Retry。
- Permission：HTTP 403 独立映射为 `StatePanel.permission`。
- Success：查询成功且存在知识库时恢复原工作台内容；Success 不覆盖业务数据。

## 局部状态边界

文档、版本、Chunk 和 Retrieval 属于页面内渐进式区域。本轮保留表格 `v-loading`、保存按钮 loading、检索 loading 等局部反馈，不用页面级 StatePanel 替换它们。

Retrieval 无结果仍属于业务查询结果语义，不等同于页面 Error；403 检索权限保持局部错误提示。

## 兼容性

保留 `listKnowledgeBases`、`listDocuments`、`listVersions`、`listChunks`、`retrieveKnowledge` 及创建、删除、切分 API 的请求参数和响应字段。不改变知识库 → 文档 → 版本 → Chunk 选择关系以及 lexical / vector / hybrid 检索模式。

## Targeted Test

`tests/views/KnowledgeUI04.test.ts` 覆盖首屏 Loading、Success、Empty、Error、403 Permission 五态。

Dashboard 对应测试 `tests/views/DashboardUI04.test.ts` 同样使用异步首屏状态断言。

## 测试环境兼容性记录

本地 Vitest 4.1.10 反馈表明，`onMounted()` 中同步设置的页面 Loading 状态需要等待一次 Vue `nextTick()` 后再断言；直接在 `mount()` 返回后断言会读取首次渲染的默认 `empty` 状态。该问题属于测试时序问题，不应修改生产页面状态机以迎合测试。

同时，Dashboard / Knowledge 测试中使用的 `v-loading` 指令在单元测试环境并未注册，会产生 Vue warning。测试通过 global directive stub 明确声明该依赖，避免 warning 干扰 targeted test 输出，不改变生产行为。

Knowledge Success 测试不再依赖 `PageToolbar` 的文本 stub，而是验证真实成功工作区的 `.grid` 容器存在，避免把子组件 stub 的渲染策略误当成页面 Contract。

## 验证

```powershell
cd frontend
npm test -- tests/views/DashboardUI04.test.ts
npm test -- tests/views/KnowledgeUI04.test.ts
npm test -- tests/components/StatePanel.test.ts
npm run build
npm run test:gate
npm run test:final
```

远端 GitHub 操作不执行本地 Node/Vitest，因此测试必须在本地实际运行后再标记通过。
