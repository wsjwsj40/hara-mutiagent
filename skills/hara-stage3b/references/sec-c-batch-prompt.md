# Stage 3B C 评级批处理提示词

仅用于隔离子任务。该子任务只判断可控性 C，不判断 S，不判断 E，不计算 ASIL。

## 上下文

只读取：

- 当前批次上下文 JSON
- `knowledge-base/automotive/hara/common/04-risk_assessment-c.md`

不要读取 S/E 知识库、`sec-merge-safety.md` 或 `04-risk_assessment.md` 索引。

## 提示词

```text
你是 HARA 可控性 C 评级专家。请只对下面这一批场景判断 C，并只输出 JSON 数组。

输入：
- MF_ID: <MF_ID>
- Stage 3B 批次上下文（最多 5 条场景）
- 04-risk_assessment-c.md 中的 C 评级定义、驾驶员反应时间和可用操作规则

任务：
1. 判断相关人员能否避免伤害。
2. 分析感知来源、反应时间、可用操作、空间约束、驾驶员是否在车上。
3. 注意：告警只是因素之一，不能自动等价为可控。
4. 根据 C 评级规则判断 `控制能力 'C'`。
5. 写入 `C评级推理`，必须包含感知来源、反应时间、可用操作、空间约束、参考规则、C等级、C理由。

输出：
只输出 JSON 数组。每个元素必须包含：
- List_No
- C-解释
- 控制能力 'C'
- C评级推理

禁止输出 Markdown、解释文字、代码围栏或顶层对象。

批次上下文：
<STAGE3B_BATCH_CONTEXT_JSON>
```
