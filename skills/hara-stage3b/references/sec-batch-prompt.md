# Stage 3B 子任务通用约束

本文件只定义 S/E/C/FTTI batch worker 的共同边界。维度专用提示词见 `sec-s-batch-prompt.md`、`sec-e-batch-prompt.md`、`sec-c-batch-prompt.md`、`sec-ftti-batch-prompt.md`。

## 通用输入

- 一个 `stage3b_<MF_ID>_batchXX_context.json`
- 当前维度的 prompt 文件
- 当前维度的唯一知识库文件

不要读取完整 Stage3A 文件、其他 batch、其他 MF、其他 SEC 维度知识库或 `04-risk_assessment.md` 索引。

## 通用输出

每个子任务写入一个 UTF-8 JSON array 文件：

- S：`output/<RUN_ID>_stage3b_<MF_ID>_batchXX_s.json`
- E：`output/<RUN_ID>_stage3b_<MF_ID>_batchXX_e.json`
- C：`output/<RUN_ID>_stage3b_<MF_ID>_batchXX_c.json`
- FTTI：`output/<RUN_ID>_stage3b_<MF_ID>_batchXX_ftti.json`

数组项必须与 batch context 中的 `List_No` 一一对应。不要输出 Markdown、解释文字、顶层 object 或额外字段集合。

## 禁止事项

- S/E/C 子任务不要计算 `结果ASIL`。
- S/E/C/FTTI 子任务不要生成 `safety_goal` 或 `safe_state`。
- 不要因为其他维度的预期结果修改本维度评级。
- 不要跨 batch 参考推理结论。
- 不要把 JSON 数组放在聊天响应中；只返回输出文件路径和简短状态。

## 失败处理

- 缺少输入字段：停止并报告缺失字段。
- 无法确定等级：按当前维度知识库给出保守但有依据的等级，不臆造规则。
- 输出写入失败：停止，不要把结果改为聊天正文。
- 校验或合并发现缺失：只重跑缺失的维度和 batch。
