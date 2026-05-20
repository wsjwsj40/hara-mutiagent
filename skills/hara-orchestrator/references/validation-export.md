# 校验、ASIL 校验与导出

## 使用方式

只在编排器需要验证、合并、ASIL 校验或最终导出时读取本文件。不要把本文件内容复制给各 Stage agent；Stage agent 应只接收路径和本阶段所需的窄参考。

## 目录

- JSON 语法与契约预检
- Stage 3 上下文切片与分段评审
- Stage 3A 和 Stage 3B 合并
- ASIL 计算与校验
- 合并与导出

## JSON 语法与契约预检

每个 stage JSON 写入后、进入 review 前，必须先运行 `check_stage_json.py`。如果 Stage 0-3 出现 JSON 语法错误、缺字段或数量不一致，先修复 JSON 文件，再重新运行检查；检查通过后才允许 review。

运行命令前必须先按主 `SKILL.md` 的路径规则解析 `tools/hara`。不要把工具路径拼到 `skills/hara-byd-analysis/tools/hara` 下，除非已经确认该目录真实存在。

常用命令：

```text
python tools/hara/check_stage_json.py --stage stage0 --json output/<run_id>_stage0_function_mapping.json
python tools/hara/check_stage_json.py --stage stage1 --json output/<run_id>_stage1_derive_mf.json --stage0 output/<run_id>_stage0_function_mapping.json --fix
python tools/hara/check_stage_json.py --stage stage2_slice --json output/<run_id>_stage2_<Function_ID>_mf_vehicle_hazards.json --stage1 output/<run_id>_stage1_<Function_ID>_derive_mf.json --function-id <Function_ID> --fix
# Stage2R 逐 Function_ID 评审并修正单功能片段后，再执行最终合并：
python tools/hara/merge_stage2.py --stage0 output/<run_id>_stage0_function_mapping.json --input-dir output --prefix <run_id> --out output/<run_id>_stage2_mf_vehicle_hazards.json
python tools/hara/check_stage_json.py --stage stage2 --json output/<run_id>_stage2_mf_vehicle_hazards.json --stage1 output/<run_id>_stage1_derive_mf.json --fix
python tools/hara/merge_stage2_review.py --input-dir output --stage0 output/<run_id>_stage0_function_mapping.json --prefix <run_id> --out output/<run_id>_stage2_review.json
python tools/hara/check_stage_json.py --stage stage3a --json output/<run_id>_stage3a_<MF_ID>_scenarios.json --mf-id <MF_ID> --operation-scenarios knowledge-base/automotive/hara/common/operation_scenarios.json --min-scenarios 10 --max-scenarios 20 --fix
python tools/hara/check_stage_json.py --stage stage3b --json output/<run_id>_stage3b_<MF_ID>_sec.json --stage3a output/<run_id>_stage3a_<MF_ID>_scenarios.json --mf-id <MF_ID> --min-scenarios 10 --max-scenarios 20
python tools/hara/check_stage_json.py --stage stage3 --json output/<run_id>_stage3_<MF_ID>_hara.json --mf-id <MF_ID> --stage2 output/<run_id>_stage2_mf_vehicle_hazards.json --operation-scenarios knowledge-base/automotive/hara/common/operation_scenarios.json --min-scenarios 10 --max-scenarios 20 --fix
python tools/hara/check_stage_json.py --stage stage4 --json output/<run_id>_stage4_sg_sum.json --hara output/<run_id>_before_stage4_check.json --fix
```

如果报 `json_syntax_error`，根据报错行列修复缺逗号、缺引号、尾随逗号、括号不闭合等问题，不要继续导出 Excel。

## Stage 3 上下文切片

Stage3A/3AR/3B/3BR 不直接读取完整 Stage0/Stage2。Stage3 前只把 Stage2 中产生的 MF 拆成一 MF 一个上下文包；功能背景复用 Stage1 的 `stage1_context_<Function_ID>.json`。

```text
python tools/hara/prepare_stage3_context.py mf-context --stage2 output/<run_id>_stage2_mf_vehicle_hazards.json --stage1-context-dir output --all --prefix <run_id> --out-dir output
```

单个 MF：

```text
python tools/hara/prepare_stage3_context.py mf-context --stage2 output/<run_id>_stage2_mf_vehicle_hazards.json --stage1-context-dir output --mf-id <MF_ID> --prefix <run_id> --out output/<run_id>_stage3_context_<MF_ID>.json
```

Stage3B 评级前生成批次上下文：

```text
python tools/hara/prepare_stage3_context.py sec-batches --context output/<run_id>_stage3_context_<MF_ID>.json --stage3a output/<run_id>_stage3a_<MF_ID>_scenarios.json --mf-id <MF_ID> --prefix <run_id> --out-dir output --batch-size 5
```

Stage3AR 场景评审前生成批次上下文：

```text
python tools/hara/prepare_stage3_context.py stage3a-review-batches --context output/<run_id>_stage3_context_<MF_ID>.json --stage3a output/<run_id>_stage3a_<MF_ID>_scenarios.json --mf-id <MF_ID> --prefix <run_id> --out-dir output --batch-size 5
```

Stage3BR SEC 评审前生成批次上下文：

```text
python tools/hara/prepare_stage3_context.py stage3b-review-batches --context output/<run_id>_stage3_context_<MF_ID>.json --stage3a output/<run_id>_stage3a_<MF_ID>_scenarios.json --stage3b output/<run_id>_stage3b_<MF_ID>_sec.json --mf-id <MF_ID> --prefix <run_id> --out-dir output --batch-size 5
```

## Stage 3A 和 Stage 3B 合并

Stage3BR 完成后，必须先合并 Stage3A 和 Stage3B 的 JSON 文件：

```text
python tools/hara/merge_stage3.py --stage3a output/<run_id>_stage3a_<MF_ID>_scenarios.json --stage3b output/<run_id>_stage3b_<MF_ID>_sec.json --output output/<run_id>_stage3_<MF_ID>_hara.json
```

对每个 MF 执行合并，生成完整的 HARA JSON 文件并通过 `--stage stage3` 后，才能进入 Stage4。

## ASIL 计算与校验

模型负责判断 S/E/C 和解释理由；最终 `结果ASIL` 必须由工具校验。

本项目采用 S/E/C 后缀求和规则：

```text
score = S后缀 + E后缀 + C后缀
score <= 6 => QM
score == 7 => A
score == 8 => B
score == 9 => C
score >= 10 => D
```

示例：

```text
S3 + E4 + C3 = 10 => D
S3 + E3 + C3 = 9 => C
S2 + E4 + C2 = 8 => B
```

重要顺序：所有 MF 的 Stage3AR、Stage3BR 完成并修正，且合并后的 Stage3 HARA 通过 `--stage stage3` 后，直接进入 Stage4。标准流程不再调用 `apply_asil_matrix.py`；如果 `check_stage_json.py` 报 `asil_mismatch_with_sec` 或 `asil_cannot_be_calculated_from_sec`，应退回 Stage3B 修正 S/E/C 或 `结果ASIL`，不要用脚本自动覆盖语义产物。

## 合并与导出

文本质量、场景合理性和运动方向由 Stage3AR 评审；S/E/C、FTTI、安全目标和安全状态由 Stage3BR 评审；合并完整性、Stage2 对齐和枚举格式由 `check_stage_json.py --stage stage3` 校验。脚本只承担确定性校验与格式归一化，不再用脚本自动改写语义文本。

Stage4 中只有 `操作模式` 由模型填写。`generate_stage4_sg.py` 会在同一 `MF_ID` 内按相同 `安全目标` 汇总 HARA 非 QM 场景：`ASIL Level` 取该 MF/安全目标组合内最高值，`FTTI(ms)` 取最小值，不同 MF 不合并，其他派生字段由工具生成，并把 `操作模式` 标为 `待Stage4模型填写`。Stage4 agent 填完操作模式后，必须用合并 HARA 校验：

```text
python tools/hara/generate_stage4_sg.py --stage-dir output --prefix <run_id> --out output/<run_id>_stage4_sg_sum.json
python tools/hara/hara_stage_merge.py --stage-dir output --prefix <run_id> --out output/<run_id>_before_stage4_check.json
python tools/hara/check_stage_json.py --stage stage4 --json output/<run_id>_stage4_sg_sum.json --hara output/<run_id>_before_stage4_check.json --fix
```

最终 `validate_hara_json.py` 会重建 Stage4 派生字段，但会保留已填写的 `操作模式`。

合并阶段 JSON：

```text
python tools/hara/hara_stage_merge.py --stage-dir output --prefix <run_id> --out output/<run_id>.json
```

导出 Excel：

```text
python tools/hara/run_hara_export.py --json output/<run_id>.json --out output/<run_id>.xlsx --mode basic
```

也可以把任意 stage 文件传给 `run_hara_export.py`，由工具按同目录同前缀自动合并：

```text
python tools/hara/run_hara_export.py --json output/<run_id>_stage4_sg_sum.json --out output/<run_id>.xlsx --mode basic
```

导出前自检：

- 所有非 `nan` 且 `field_reasoning.推理.是否有安全风险=是` 的功能故障都出现在 `mf_vehicle_hazards`；适用但无安全风险的故障只保留在 Stage1，不进入 Stage2。
- `mf_vehicle_hazards` 中所有 MF 都出现在 `hara`。
- 每个 MF 都有 10 到 20 条 HARA 场景。
- `结果ASIL` 已由工具校验。
- Stage3AR、Stage3BR、Stage3 合并校验和 Stage4R 均已通过；若发现语义质量问题，应由对应 review agent 修正或重跑相关阶段。
- 合并后的 HARA `List_No` 是从 1 开始的全局连续序号。
- Excel 文件真实生成，空白字段在 Excel 中显示为空白单元格。
