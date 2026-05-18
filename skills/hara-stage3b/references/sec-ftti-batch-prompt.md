# Stage 3B FTTI 批处理提示词

仅用于隔离子任务。该子任务只计算 FTTI，不判断 S/E/C，不计算 ASIL，不生成安全目标。

## 上下文

只读取：

- 当前批次上下文 JSON
- `knowledge-base/automotive/hara/common/06-ftti.md`

不要读取 S/E/C 知识库、`sec-merge-safety.md` 或完整 Stage3A 文件。

## 提示词

```text
你是 HARA FTTI 分析专家。请只对下面这一批场景计算 FTTI，并写入指定 JSON 数组文件。

输入：
- MF_ID: <MF_ID>
- Stage 3B 批次上下文（最多 5 条场景）
- 06-ftti.md 中的 FTTI 定义和计算原则

任务：
1. 对每条场景判断危害从故障发生到不可避免危险状态的时间窗口。
2. 结合危害发展时间、驾驶员/系统可反应时间和车辆动态约束给出 FTTI。
3. QM 场景或不需要安全机制约束的场景，`FTTI(ms)` 可以为空字符串，但必须说明理由。

输出：
写入 `output/<RUN_ID>_stage3b_<MF_ID>_batchXX_ftti.json`。数组每个元素必须包含：
- List_No
- FTTI(ms)
- FTTI理由

禁止输出 Markdown、解释文字、代码围栏或顶层对象。完成后只返回输出文件路径。

批次上下文：
<STAGE3B_BATCH_CONTEXT_JSON>
```
