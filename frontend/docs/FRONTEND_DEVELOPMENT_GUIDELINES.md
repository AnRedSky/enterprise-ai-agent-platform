# 前端开发准则

> 本文件是 `frontend` 专用工程开发准则。项目级工程规则以 `docs/01-governance/DEVELOPMENT.md` 为最高约束；本文件只补充前端实现、验证、UI 和提交方面的具体执行规则。

## 1. 后端优先与 Contract 对齐

前端不得根据猜测设计后端能力。执行顺序固定为：

```text
Backend Domain / API Contract
        ↓
Backend Tests / Real Acceptance
        ↓
Frontend API Types
        ↓
Frontend View / Component
        ↓
Vitest
        ↓
Real API / E2E
```

后端尚处于开发中、Contract 尚未稳定或 Runtime Acceptance 尚未完成的能力，只允许记录为待实施任务，不得作为正式前端功能基线。

## 2. 前端实现边界

- 前端负责展示、交互、表单校验、状态呈现和用户操作编排。
- 后端负责业务规则、权限、tenant boundary、状态机、幂等、重试、事务和可靠投递事实。
- 前端不得复制后端业务计算规则作为第二套事实来源。
- API 类型必须直接对应正式 Contract；发现 Contract 变化时先同步类型，再调整页面。
- 技术标识如资源 ID、事件类型、错误码、Trace ID 可以保留原文，但必须配中文字段说明。

## 3. UI 文本

- 用户可见文本统一使用通俗中文。
- 不为了中文化复制一套新的 UI；在现有页面结构上渐进修正。
- 状态枚举必须通过统一映射展示；未知值显示“未知状态（技术值）”。
- 禁止把 `error.message`、HTTP 错误正文、后端异常堆栈直接展示给用户。
- 错误提示采用“发生了什么 + 下一步怎么办”的表达方式。
- 按钮优先使用用户动作，如“保存”“查看详情”“重新投递”，而不是接口或代码术语。
- 完整文本规则见 `FRONTEND_UI_TEXT_GUIDELINES.md`。

## 4. 页面状态完整性

每个业务页面必须明确处理：

- Loading：请求期间的反馈；
- Empty：没有数据时的业务说明和必要的下一步；
- Error：用户可理解的错误提示；
- Success：操作成功后的明确反馈；
- Permission：无权限时的说明和不可操作状态。

列表页面还必须处理分页、刷新、筛选条件和请求失败后的恢复行为。

## 5. 公共组件与 UI 一致性

重复出现的页面模式应优先复用公共组件或公共样式，而不是复制实现。优先统一：

- 页面标题区；
- 查询工具栏；
- 指标卡；
- 数据表格；
- 详情面板；
- 空状态；
- 错误提示；
- 确认对话框；
- 状态标签。

不得为了局部视觉效果破坏已有信息架构和交互行为。

## 6. 安全

- Secret、Token、API Key 等敏感信息不得在 UI 明文展示。
- 前端不得绕过后端直接调用受保护的目标 Endpoint。
- Replay、删除、归档等危险操作必须经过确认，并展示业务影响。
- tenant-scoped 数据必须以服务端返回事实为准，前端不得自行扩大数据范围。

## 7. 测试

测试实现只放在 `frontend/tests/`；脚本编排只放在 `frontend/scripts/test/`。

标准验证顺序：

```text
npm test -- <targeted-test>
        ↓
npm test
        ↓
npm run build
        ↓
npm run test:gate
```

涉及真实后端时，再独立执行对应 Backend Real API / E2E 验收。没有实际执行的结果不得记录为“通过”。

## 8. 测试覆盖要求

新增或修改业务页面至少验证：

- 正常数据展示；
- 空数据；
- 加载状态；
- API 失败；
- 后端技术错误值不会直接污染用户提示；
- 已知状态映射；
- 未知状态安全回退；
- 关键按钮启用/禁用；
- 关键 API 调用参数；
- 成功后的页面状态刷新。

## 9. 文档与任务记录

每个具有独立工程意义的前端功能，在提交前必须检查 `frontend/docs`：

- 新增设计决策；
- Contract 对齐说明；
- 页面行为变化；
- 测试验收结果；
- 已知限制；
- 后续任务。

长期任务统一维护在 `FRONTEND_TASK_EXECUTION_PLAN.md`；路线图维护在 `FRONTEND_LONG_TERM_ROADMAP.md`。文档不能代替实际代码实现。

## 10. 原子提交

- 直接基于 `main`，禁止创建功能分支。
- 一个提交只解决一个功能、一个修复或一个具有独立工程意义的文档任务。
- 同一功能的源码、测试和设计记录应放在同一个原子提交中。
- 测试反馈产生的新问题必须形成新的语义单一提交。
- 禁止通过多个文档提交制造虚假的进度记录。

## 11. 完成定义

一个前端任务只有在“功能实现 + 测试 + 构建 + 必要文档”均完成后才能标记完成。涉及真实后端的任务还必须完成实际联调或明确记录阻塞原因。

## 12. 当前长期执行优先级

```text
稳定 Backend Contract
    ↓
Agent / Workflow / Runtime 核心闭环
    ↓
Knowledge / Tool
    ↓
Organization / Model Provider
    ↓
Audit / Integration
    ↓
2.10-I 新增能力（以后端 Runtime Acceptance 为准）
    ↓
设计系统 / E2E / 性能 / 无障碍 / 平台化
```
