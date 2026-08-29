# LT-07 Agent Evaluation / Quality

## 1. 目标
建立 Agent、Workflow、RAG、Tool 调用和模型版本的持续质量评估体系，使生产发布不仅验证“能运行”，还验证“结果质量”。

## 2. 当前状态
**待立项。** 当前已有 Runtime、Trace、Audit、Model Governance 和测试体系，但没有完整的 Agent Quality Evaluation 平台。

## 3. 主要缺口
- Evaluation Dataset / Golden Set；
- 自动评分与人工评分；
- LLM-as-Judge 与规则评分边界；
- Agent trajectory / tool-use 质量指标；
- RAG retrieval/grounding 指标；
- Prompt/model/version regression；
- 在线反馈采集；
- Quality gate 与发布阻断；
- 评测结果版本化和可追溯。

## 4. 长期拆解
评测模型 → Dataset → Offline Evaluation → Online Feedback → Regression → Release Quality Gate → Dashboard → 持续优化。

## 5. 完成判定
核心 Agent/Workflow 具备可重复评测集、质量指标、版本对比、回归门禁和人工反馈闭环。
