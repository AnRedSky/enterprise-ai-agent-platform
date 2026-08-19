# Phase 1.4-F/G：Vue Knowledge / Retrieval Debug 验收

> 当前阶段基于 Phase 1.4-D Runtime + Knowledge 联调基线，继续完成前端 Knowledge Workbench 与 Retrieval Debug 的可用性、错误处理和可追溯性。

## 已落地

- Knowledge Workbench：Knowledge Base → Document → Version → Chunk。
- Retrieval Debug：query / top-k / Knowledge Base scope。
- Retrieval loading 状态。
- Retrieval 空结果与输入校验。
- Retrieval API 错误态，不向页面冒泡 rejected Promise。
- Retrieval Result：来源、Score、Citation、Chunk 内容。
- Citation Detail：Document、Score、Citation、Source URI、正文。
- 清空检索状态。
- 保持前端 TypeScript 源码，不引入生成式 `.js/.jsx` 源文件。

## 自动化验收

```powershell
cd frontend
npm test
npm run build
```

必须同时通过；不能只依据 Vitest 通过判断阶段完成。

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
9. 切换 Knowledge Base 后检索结果应清空并重新限定范围。
10. 清空 Retrieval Debug 后页面恢复初始空态。

## 下一步

- 补齐 Knowledge Base / Document 编辑体验。
- 增加分页与更明确的 retrieval filter。
- 将 Retrieval Debug 与 Runtime Citation 展示进一步串联。
- 补齐浏览器级前端验收后进入 Phase 1.5 Workflow / Governance。
