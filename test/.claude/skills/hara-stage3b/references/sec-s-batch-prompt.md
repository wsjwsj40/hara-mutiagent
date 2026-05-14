# Stage 3B S 评级批处理提示词

仅用于隔离子任务。该子任务只判断严重度 S，不判断 E，不判断 C，不计算 ASIL。

## 上下文

只读取：

- 当前批次上下文 JSON
- `knowledge-base/automotive/hara/common/04-risk_assessment-s.md`

不要读取 E/C 知识库、`sec-merge-safety.md` 或 `04-risk_assessment.md` 索引。

## 提示词

```text
你是 HARA 严重度 S 评级专家。请只对下面这一批场景判断 S，并只输出 JSON 数组。

输入：
- MF_ID: <MF_ID>
- Stage 3B 批次上下文（最多 5 条场景）
- 04-risk_assessment-s.md 中的 S 评级定义、碰撞速度表和必要伤害规则

任务：
1. 对每条场景识别有风险的人员。
2. 分析可能的伤害后果：
   - 碰撞类：识别碰撞对象、碰撞方向/类型、碰撞速度或相对速度。
   - 非碰撞类：说明伤害机理。
3. 根据 S 评级规则判断 `Severity 'S'`。
4. 写入 `S评级推理`，必须包含伤害分析、碰撞对象、碰撞速度、参考规则、S等级、S理由。

输出：
只输出 JSON 数组。每个元素必须包含：
- List_No
- 有风险的人员
- 可能的后果('S'的理由)
- Severity 'S'
- S评级推理

禁止输出 Markdown、解释文字、代码围栏或顶层对象。

批次上下文：
<STAGE3B_BATCH_CONTEXT_JSON>
```
