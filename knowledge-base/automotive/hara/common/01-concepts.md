# HARA 基础概念
HARA（危害分析与风险评估，Hazard Analysis and Risk Assessment）用于在 ISO 26262 概念阶段识别功能项的故障行为，基于操作场景形成危险事件，并通过安全性、暴露性、可控性确定风险等级和ASIL。

## 1. 目标与适用时机
- 识别功能项在车辆层面的潜在危险行为及其人身伤害风险。
- 为不可接受风险定义安全目标、安全状态和 FTTI。
- 适用于新功能项开发、重大变更、运行条件显著变化或新增关键用例时的概念阶段分析。

## 2. 分析起点
- 先明确项目定义：功能项名称、功能项具体描述。
- HARA 的核心链路通常是：
  `item/function extraction -> malfunctioning behavior -> hazard -> operational situation -> hazardous event -> S/E/C -> ASIL -> safety goal`
- 危害事件不是单独的故障，也不是单独的场景，而是异常行为在特定场景下引发的人身伤害风险。

## 3. 基本术语
- Item：被分析的车辆级系统或功能集合。
- Function：item 对外提供的功能能力。
- Design Intent：设计意图是功能在正常情况下应实现的目标行为。
- Fault：可能导致异常的内部原因，例如硬件故障、软件错误或信号异常。
- Failure：功能未能按预期完成的结果。
- Malfunctioning behavior：item 或功能在车辆层面表现出的异常行为。
- Hazard：由 malfunctioning behavior 可能导致的潜在人身伤害来源。
- Operational situation：危险事件发生的运行场景和环境条件。
- Hazardous event：hazard 与 operational situation 的结合。
- Severity：危险事件可能造成的人身伤害严重度。
- Exposure：operational situation 出现的频率。
- Controllability：相关人员避免伤害的现实能力。
- Safety goal：为避免或控制不可接受风险而定义的顶层安全目标。
- Safe state：系统进入或保持的、可以避免危险事件继续发展的安全状态。
- FTTI：容错时间间隔（Fault Tolerant Time Interval），从故障发生到危险无法避免之间允许的时间窗口。

HARA 关注车辆级危害和人员伤害，不直接以内部故障、软件缺陷或组件失效作为最终分析对象。