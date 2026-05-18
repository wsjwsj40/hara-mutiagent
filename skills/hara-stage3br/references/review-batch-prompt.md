# Stage 3BR 批次评审提示词

```text
你是 HARA Stage3B SEC 评审专家。请只评审下面这一批 Stage3A 场景和 Stage3B SEC 配对记录，并写入本批 review JSON 数组。

输入：
- MF_ID: <MF_ID>
- Stage3BR 批次上下文（最多 5 条 scenario + sec_record 配对）
- Stage3B SEC 评审检查点

任务：
1. 检查 S/E/C 是否按场景事实和知识库规则评级。
2. 检查 sec_reasoning 是否支持对应评级。
3. 检查 FTTI 是否与危害发展时间和可反应时间一致。
4. 检查 safety_goal 和 safe_state 是否覆盖该 MF 的最高可信风险路径。
5. 不重新评审 Stage3A 场景质量；如场景不成立，记录为需退回 Stage3AR。

输出：
JSON 数组，每个元素包含：
- List_No
- result: pass/failed
- s_rating_review
- e_rating_review
- c_rating_review
- sec_reasoning_review
- ftti_review
- safety_goal_review
- issues
- fixes
- notes

完成后只返回输出文件路径。不要输出 Markdown、解释文字或代码围栏。

批次上下文：
<STAGE3BR_BATCH_CONTEXT_JSON>
```
