# HARA 风险评估

本文件是风险评估知识库索引。不要把本文件作为 S/E/C 详细规则全文加载；请按当前任务只读取对应的窄知识库文件。

## 拆分文件

- 严重度 S：`04-risk_assessment-s.md`
- 暴露度 E：`04-risk_assessment-e.md`
- 可控性 C：`04-risk_assessment-c.md`
- ASIL 映射：`04-risk_assessment-asil.md`

## 总原则

HARA 风险评估基于 item definition、hazardous event 和运行场景，对每个危害事件分别判断严重度 S、暴露度 E 和可控性 C。S/E/C 难以明确区分时，应选择更保守的较高等级，并在解释字段中说明依据。

- S 只评价人员伤害严重度，不评价财产损失或功能可用性。
- E 评价运行场景的出现概率，不评价故障发生概率。
- C 评价相关人员避免伤害的现实能力，不只评价系统是否有告警。
- ASIL 由 S/E/C 结果计算，不应先设定 ASIL 再倒推 S/E/C。
