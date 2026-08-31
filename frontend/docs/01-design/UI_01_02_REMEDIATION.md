# UI-01 + UI-02 整改记录

## 状态

**进行中：首轮基础系统整改已实现。**

## 本轮目标

暂停新增业务功能，先解决系统级 UI 缺乏企业级一致性的问题。UI-01 负责建立 Design Tokens 与公共控件基线；UI-02 负责重构 Application Shell 的视觉与响应式基线。

## 实施内容

### UI-01

- 建立统一颜色、文字、间距、圆角、阴影和布局 Token；
- 建立 reset / typography / Element Plus component 层；
- 让现有 `global.css` 成为应用级布局入口，避免业务页面继续散落具体色值；
- 保留现有 Element Plus 技术栈，不引入新的 UI 框架。

### UI-02

- 统一侧边栏品牌、工作区、导航分组和系统状态区域；
- 统一顶部上下文栏、搜索入口、环境标识和用户菜单；
- 使用 Token 替代 Shell 中的硬编码视觉参数；
- 保留既有路由与信息架构，不改变业务 Contract；
- 优化 900px / 700px 以下的紧凑布局，降低小屏横向溢出风险；
- 增强键盘焦点和 reduced-motion 支持。

## 根因与解决方案

当前 UI 的主要问题不是单个页面缺少样式，而是视觉参数和 Shell 规则没有形成稳定的全局设计系统：颜色、间距、控件尺寸、卡片和 Dialog 风格散落在全局 CSS 与组件 scoped CSS 中。解决方案是先收敛 Token 和 Shell，再逐页整改。

## 暂不处理

本任务不新增 Agent、Workflow、Runtime、Provider 等业务能力；不修改后端 API Contract；不改变现有业务路由。

## 验收

本轮代码提交前需执行项目既有 targeted Vitest、全量 Vitest、production build 和 frontend regression gate。视觉验收按 1440 / 1280 / 1024 / 768 / 390 viewport 检查 Shell 与公共控件。

未实际执行的测试不得标记为通过。
