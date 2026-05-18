# Stage 3B 合并、ASIL、安全目标

本文件只供 Stage3B 总控读取。S/E/C/FTTI 子任务不要读取本文件。

## 输入

- S batch 数组：`List_No`、`有风险的人员`、`可能的后果('S'的理由)`、`Severity 'S'`、`S评级推理`
- E batch 数组：`List_No`、`E-解释`、`暴露频率'E'`、`E评级推理`
- C batch 数组：`List_No`、`C-解释`、`控制能力 'C'`、`C评级推理`
- FTTI batch 数组：`List_No`、`FTTI(ms)`、`FTTI理由`
- Safety 文件：`safety_goal`、`safe_state`

## 合并规则

1. 使用 `merge_sec_batches.py` 合并，不要手写最终 `sec_records`。
2. 以 `List_No` 对齐 S/E/C/FTTI。
3. 合并后由 `stage3b` check 判断是否缺少 S、E 或 C；发现缺失时重跑对应维度。
4. 不改写子任务评级结论；合并脚本只做字段拼接和可解析情况下的 `结果ASIL` 派生。
5. `sec_reasoning` 由三个维度推理对象组成：

```json
{
  "S评级推理": {},
  "E评级推理": {},
  "C评级推理": {}
}
```

6. 最终 `sec_records` 按 `List_No` 升序排列，数量必须等于 Stage3A `scenarios` 数量。

## ASIL

`结果ASIL` 由 `merge_sec_batches.py` 根据 `Severity 'S'`、`暴露频率'E'`、`控制能力 'C'` 派生。总控不要为了得到更高 ASIL 改写 S/E/C。

`check_stage_json.py --stage stage3b --stage3a ...` 会复算并校验 ASIL、公式片段、S/E/C 推理一致性和 Stage3A 对齐。如果评级字段无法解析为 `S0-S3`、`E0-E4`、`C0-C3`，修正对应子任务输出。

## Safety

`safety_goal` 和 `safe_state` 是当前 MF 级别输出，不是每条场景一条。

- 基于最高可信风险路径生成。
- 参考 `knowledge-base/automotive/hara/common/05-safety_goal.md`。
- Safety 文件格式见 `json-contracts.md`。

## FTTI

FTTI 参考 `knowledge-base/automotive/hara/common/06-ftti.md`。

- 非 QM 场景应给出 `FTTI(ms)` 和 `FTTI理由`。
- QM 场景的 `FTTI(ms)` 可以为空字符串。

## 命令

```text
python tools/hara/merge_sec_batches.py --s-batches output/<RUN_ID>_stage3b_<MF_ID>_batch*_s.json --e-batches output/<RUN_ID>_stage3b_<MF_ID>_batch*_e.json --c-batches output/<RUN_ID>_stage3b_<MF_ID>_batch*_c.json --ftti-batches output/<RUN_ID>_stage3b_<MF_ID>_batch*_ftti.json --safety output/<RUN_ID>_stage3b_<MF_ID>_safety.json --output output/<RUN_ID>_stage3b_<MF_ID>_sec.json --meta-mf-id <MF_ID> --meta-run-id <RUN_ID>
```
