# Frontend UI Design System

> UI-01 ～ UI-03 的单一事实来源。目标是建立企业级 SaaS 的统一视觉语言，而不是为单个业务页面制作独立皮肤。

## 1. Design principles

1. **Information first**：高信息密度场景保持清晰层级，减少装饰性视觉。
2. **Consistent semantics**：颜色、状态、间距、圆角、阴影和控件尺寸由 Design Tokens 统一管理。
3. **Progressive disclosure**：复杂信息按概览 → 列表 → 详情 → 诊断/操作逐层展开。
4. **Operational clarity**：成功、警告、失败、无权限和空状态必须有明确语义与恢复动作。
5. **Responsive by contract**：1440 / 1280 / 1024 / 768 / 390 为视觉验收基线。

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

## 4. UI-03 Public page patterns

公共页面必须优先采用以下模式，禁止每个业务页面自行设计同义结构：

| Pattern | Component | 使用规则 |
|---|---|---|
| 页面标题 | `PageHeader` | 页面唯一主标题；描述和主操作分别位于标题区两侧 |
| 页面工具栏 | `PageToolbar` | 筛选、搜索、批量操作、视图切换等列表级操作 |
| 指标卡 | `MetricCard` | 展示关键数量/指标，可附趋势或辅助说明 |
| 内容卡片 | `SurfaceCard` | 组织相关列表、配置、摘要和次级内容 |
| 数据表格 | Element Plus `el-table` + 全局规则 | 高密度数据优先表格，操作列保持稳定 |

### PageHeader

- 一个页面只允许一个一级标题；
- 标题、描述、操作形成稳定的三段层级；
- 窄屏下操作换行/纵向排列，不挤压标题；
- 页面标题不承载业务状态颜色。

### PageToolbar

- 工具栏与标题区保持独立间距；
- 左侧放上下文/批量信息，右侧放筛选、搜索和主要操作；
- 移动端允许换行，但操作顺序必须保持一致。

### MetricCard

- 标签 → 主值 → 趋势/辅助说明；
- 数值采用等宽数字，避免刷新时布局抖动；
- 不使用大面积渐变或装饰性图表代替信息层级。

### SurfaceCard

- 使用统一边框、圆角和轻阴影；
- Header 用于标题/说明/局部操作，Body 承载实际内容；
- 卡片不是页面布局的强制容器，避免过度卡片化。

## 5. Table / Form / Dialog visual baseline

- 表头使用次级文本和浅背景，行高保证企业高密度场景下的扫描效率；
- 输入控件统一中号高度和 focus ring；
- Dialog / Drawer 使用统一圆角、Header 分隔线和 Footer 操作区；
- 危险操作必须使用语义化危险色和确认流程，不仅依赖颜色区分；
- 分页统一位于内容区底部，并在窄屏下保持可操作。

## 6. Accessibility

- 所有图标按钮提供可读的 `aria-label`；
- 键盘焦点保持可见；
- 减少动态效果时遵循 `prefers-reduced-motion`；
- 不依赖颜色单独表达业务状态。

## 7. Acceptance

UI-03 完成后至少验证：`npm test`、`npm run build`、`npm run test:gate`；视觉验收补充 1440 / 1280 / 1024 / 768 / 390 五档 viewport，并检查 PageHeader、Toolbar、MetricCard、SurfaceCard、Table、Form、Dialog 的一致性。
