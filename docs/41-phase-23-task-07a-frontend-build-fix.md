# Phase 23 / Task 07-A：Frontend Build Type Declaration Fix

## 1. 本阶段背景

本阶段根据人工测试反馈修复 `frontend/npm run build` 的 44 个 TypeScript 声明错误。

原始错误全部出现在 `node_modules` 的第三方声明文件，主要涉及：

- `@vueuse/core` 的 Web Bluetooth 类型
- `element-plus` 的 `GlobalComponents` 泛型约束
- `element-plus` 的 JSX 类型
- `element-plus` 的 `h` 自引用声明

## 2. 根因判断

项目当前采用 Vue 3 + TypeScript + vue-tsc + Element Plus。应用源码并未出现在本次 44 个错误列表中，错误集中在第三方 `.d.ts` 文件。

因此本阶段不修改业务 Vue 页面，也不通过修改 `node_modules` 绕过问题。

## 3. 已实施修复

修改：

`frontend/tsconfig.app.json`

增加：

```json
"types": ["vite/client", "element-plus/global"],
"skipLibCheck": true
```

其中：

- `element-plus/global` 显式加载 Element Plus 全局组件类型声明；
- `skipLibCheck` 仅跳过第三方声明文件的类型检查，继续严格检查项目自身 TypeScript / Vue 源码；
- 未修改 `node_modules`；
- 未删除任何错误；
- 未关闭 `strict`。

## 4. Git 提交

Commit：`8afe568e738b7caee0f1d450c76e0715efd088ea`

提交信息：

`fix: align frontend declaration checking with Vue and Element Plus`

## 5. 验收状态

代码修复已经提交，但由于项目采用人工测试反馈模式，本阶段**不提前声明本地 build 已通过**。

需要开发环境执行：

```bash
cd frontend
npm run build
```

只有实际输出成功后，才能将 Frontend Build 标记为 PASS。

## 6. 下一阶段入口

Build PASS 后进入 Frontend Test：

```bash
npm test
```

若 Build 仍失败，优先反馈新的第一处错误，不继续扩展业务功能。
