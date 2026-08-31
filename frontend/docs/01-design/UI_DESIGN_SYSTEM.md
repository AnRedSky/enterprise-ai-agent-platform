# Frontend UI Design System

> UI-01 基础设计系统与 UI-02 应用 Shell 的单一事实来源。目标是建立企业级 SaaS 的统一视觉语言，而不是为单个业务页面制作独立皮肤。

## 1. Design principles

1. **Information first**：高信息密度场景保持清晰层级，减少装饰性视觉。
2. **Consistent semantics**：颜色、状态、间距、圆角、阴影和控件尺寸由 Design Tokens 统一管理。
3. **Progressive disclosure**：复杂信息按概览 → 列表 → 详情 → 诊断/操作逐层展开。
4. **Operational clarity**：成功、警告、失败、无权限和空状态必须有明确语义与恢复动作。
5. **Responsive by contract**：1440 / 1280 / 1024 / 768 / 390 为后续视觉验收基线。

## 2. UI-01 Token architecture

Token 文件：

- `src/styles/tokens.css`：颜色、文字、间距、圆角、阴影、布局尺寸等基础 Token；
- `src/styles/reset.css`：浏览器基础行为与可访问性焦点规则；
- `src/styles/typography.css`：字体、标题、正文和等宽文本层级；
- `src/styles/components.css`：Element Plus 的全局控件视觉约束；
- `src/styles/global.css`：应用布局变量和页面容器规则。

业务页面不得重新定义同义颜色、间距或圆角；确有领域语义时应新增语义 Token，而不是复制具体色值。

## 3. UI-02 Application Shell

Application Shell 固定由以下区域组成：

- 左侧主导航：品牌、工作区、分组导航、平台状态；
- 顶部上下文栏：侧栏控制、面包屑、全局搜索、帮助、通知、环境、用户菜单；
- 内容区：统一页面容器和路由过渡。

导航仍保持现有企业信息架构，不改变业务路由，只统一视觉、密度和响应式行为。700px 以下进入紧凑导航模式，避免横向溢出。

## 4. Component rules

公共组件必须单一职责、无领域业务规则、可独立测试。优先复用 PageHeader、Toolbar、MetricCard、DataTable、DetailPanel、StatusTag、EmptyState、ErrorState、ConfirmDialog。

## 5. Accessibility

- 所有图标按钮提供可读的 `aria-label`；
- 键盘焦点保持可见；
- 减少动态效果时遵循 `prefers-reduced-motion`；
- 不依赖颜色单独表达业务状态。

## 6. Acceptance

UI-01 + UI-02 完成后，必须至少验证：`npm test`、`npm run build`、`npm run test:gate`；视觉验收补充 1440 / 1280 / 1024 / 768 / 390 五档 viewport，并检查导航、页面容器、表格、表单、Dialog、Empty/Error/Loading 的一致性。
