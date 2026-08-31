# UI-04 KnowledgeWorkbench 状态迁移

## 范围

本轮仅迁移 `KnowledgeWorkbench.vue` 的页面级 Loading / Empty / Error / Permission / Success 状态，不修改 Knowledge API Contract，也不迁移 Tool 页面。

## 状态映射

- Loading：知识库首屏加载期间使用 `StatePanel.loading`。
- Empty：知识库查询成功且列表为空，使用 `StatePanel.empty`，提供创建入口。
- Error：知识库查询失败，使用 `StatePanel.error` 并提供 Retry。
- Permission：HTTP 403 独立映射为 `StatePanel.permission`，不与网络错误混淆。
- Success：知识库查询成功且存在数据时恢复原工作台内容；Success 不覆盖业务数据。

## 局部状态边界

文档、版本、Chunk 和 Retrieval 属于页面内的渐进式数据区域，本轮保持原有局部交互。`el-table v-loading`、保存按钮 loading、检索 loading 等局部反馈不被页面级 StatePanel 替代。

检索无结果仍属于业务查询结果语义，不等同于页面 Error；403 检索权限可以在 Retrieval 区域显示权限错误。

## 兼容性

- 保留现有 `listKnowledgeBases`、`listDocuments`、`listVersions`、`listChunks`、`retrieveKnowledge` 等调用。
- 不修改后端字段名称、请求参数或响应结构。
- 保留知识库 → 文档 → 版本 → Chunk 的逐级选择关系。
- 保留 Retrieval 的 lexical / vector / hybrid 模式。

## Targeted Test

`tests/views/KnowledgeUI04.test.ts` 覆盖首屏 Loading、Success、Empty、Error、403 Permission 五态。

## 验证

```powershell
cd frontend
npm test -- tests/views/KnowledgeUI04.test.ts
npm test -- tests/components/StatePanel.test.ts
npm run build
npm run test:gate
npm run test:final
```

远端 GitHub 操作不执行本地 Node/Vitest，因此测试必须在本地开发环境实际运行后再标记通过。
