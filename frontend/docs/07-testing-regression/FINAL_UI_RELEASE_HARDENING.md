# Frontend Final UI Release Hardening

> 基线：`main` @ 2026-08-30
> 范围：暂不推进 P2.10-I；进入整体 UI 精修与最终测试阶段。

## 1. 本阶段目标

1. 统一企业级视觉基础：颜色、间距、圆角、阴影、字号层级与表单密度。
2. 消除全局样式之间的冲突，建立单一 UI token 来源。
3. 提升桌面、平板、小屏下的可用性，并补齐键盘焦点与 reduced-motion 支持。
4. 不改变已经稳定的后端业务 Contract，不新增 P2.10-I 业务范围。
5. 最终自动化 Gate 使用全量 Vitest + production build；Real API、浏览器 E2E 和人工视觉验收独立执行。

## 2. 本次实现

### 2.1 全局 Design Tokens

`src/styles/global.css` 增加统一 token：

- 页面背景 / Surface / Border / Text 层级
- Primary / Success / Warning / Danger
- 8 / 10 / 12px 圆角层级
- 页面最大宽度、Header 高度、页面水平/垂直内边距
- 轻量阴影层级

这样页面局部样式仍可覆盖，但默认视觉基线一致。

### 2.2 Layout 与组件统一

- 侧栏统一为浅色企业控制台风格，与当前 `AppShell` 实际渲染保持一致。
- Card、Button、Input、Select、Table、Dialog、Tag、Alert、Empty 的基础密度统一。
- 表格 Header、正文颜色与边界层级统一。
- Dialog Header/Footer 增加清晰分隔，提升复杂管理操作的扫描效率。

### 2.3 可访问性与交互

- 增加统一 `:focus-visible` 焦点样式。
- 保留键盘操作路径，不通过全局样式隐藏焦点。
- 增加 `prefers-reduced-motion`，降低动画对敏感用户的影响。
- 保持原有中文用户文案与必要技术标识，不通过视觉重构改变业务语义。

### 2.4 响应式

断点保持简单明确：

| Viewport | 策略 |
|---|---|
| > 1100px | 完整桌面布局，页面最大宽度 1440px |
| 901–1100px | 缩小页面水平留白 |
| 601–900px | 收缩侧栏，隐藏非核心用户信息 |
| <= 600px | 紧凑 Header、隐藏 Breadcrumb、Dialog 使用视口内宽度 |

## 3. 最终测试策略

### 3.1 自动化 Gate

```powershell
cd frontend
npm run test:final
```

该命令执行：

1. `npm test`：全量 Vitest 回归。
2. `npm run build`：TypeScript + Vite production build。

### 3.2 分阶段测试仍然保留

此前阶段脚本继续保留：

- `npm run test:phase:p1`
- `npm run test:phase:p2`
- `npm run test:phase:p2.10`
- `npm run test:phase:p3`
- `npm run test:phase:p4`

最终阶段才执行 `test:final`，避免开发阶段产生超长全量日志。

### 3.3 浏览器 / Real API 手工验收

启动前端后依次检查：

1. 登录 → 总览。
2. 智能体、工具、知识库列表与详情。
3. 工作流 → 触发器 → Runtime。
4. 运行中心 → Trace / Audit。
5. 组织与成员 → 模型 Provider。
6. 集成中心。
7. 运行运维页面保持可进入，但本阶段不扩展 P2.10-I 功能。
8. 空数据、加载中、接口失败、权限受限状态。
9. 1366×768、1440×900、1024×768、768×1024、390×844 五组视口。
10. Tab 键完成主要交互，确认焦点可见。

## 4. 上线判定

### Blocker

- `npm test` 失败。
- `npm run build` 失败。
- 任一主导航不可达或白屏。
- 已实现后端 Contract 无法正常消费。
- 关键管理操作出现浏览器直连受保护 Destination 的行为。

### High

- 核心页面在 1024px 以下出现横向溢出。
- 错误信息泄漏 HTTP 原文或内部异常。
- 主要按钮无加载/禁用反馈。
- 键盘无法访问核心操作。

### Medium / Low

- 非核心页面间距、字号或视觉细节不一致。
- 非关键动画与微交互仍有优化空间。

## 5. 后续长期 UI 优化

最终 Gate 通过后，再按以下顺序推进：

1. 视觉基线：统一页面 Header / Toolbar / Card / Table 模板。
2. 信息密度：复杂管理页面统一筛选区、统计区、数据区结构。
3. 状态体验：Loading / Empty / Error / Success / Disabled 全状态标准化。
4. 响应式：逐页补齐复杂表格、Drawer、Dialog 和 Runtime 时间线。
5. 可访问性：键盘导航、语义标签、对比度、焦点管理。
6. 性能：路由级懒加载、资源体积、重复请求与渲染开销。
7. 最终视觉回归：固定视口截图基线 + 人工验收。

本阶段明确不把 P2.10-I 新功能混入 UI 收口，以避免在后端 Contract 尚未作为当前主线验收目标时扩大变更面。
