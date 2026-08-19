# Phase 1.4-F/G：Vue Knowledge / Retrieval Debug 验收

## 当前范围

- Knowledge Base → Document → Version → Chunk 工作台。
- Retrieval Debug：query / top-k / Knowledge Base scope。
- Retrieval loading、输入校验、错误态、空结果。
- Retrieval Result：来源、Score、Citation、Chunk 内容。
- Citation Detail：Document、Score、Citation、Source URI、正文。
- 清空检索状态。
- TypeScript-only 前端源码，禁止提交生成式 `.js/.jsx` 源文件。

## 自动化验收

```powershell
cd frontend
npm test
npm run build
```

两项必须同时通过。

## 浏览器验收

```powershell
cd frontend
npm run dev
```

1. 登录后进入 Knowledge 页面。
2. 创建并选择 Knowledge Base。
3. 创建 Document。
4. 创建 Version 并执行 Ingest。
5. 查看 Chunk。
6. 在 Retrieval Debug 输入问题并执行检索。
7. 检查 loading、空结果、错误提示。
8. 选择结果，确认 Citation Detail 与 Source URI 可追溯。
9. 切换 Knowledge Base 后检索结果清空并重新限定范围。
10. 清空 Retrieval Debug 后恢复初始空态。

## 后续

- Knowledge Base / Document 编辑体验。
- 分页与 retrieval filter。
- Retrieval Debug 与 Runtime Citation 展示串联。
- 浏览器级前端验收完成后进入 Phase 1.5 Workflow / Governance。
