# Stage 4: SG_Sum 汇总

目标：基于 ASIL 工具校验后的 HARA 数据生成安全目标汇总。

Stage 4 必须使用工具确定 MF 覆盖范围和 ASIL Level，不要让大模型自行计算或重建 ASIL。大模型可以参与安全目标/安全状态文字评审，但不能覆盖工具给出的 `MF_ID`、`ASIL Level`、QM 排除结果。

## 需要读取

- 已完成 ASIL 校验的所有 Stage 3 HARA 文件
- `knowledge-base/automotive/hara/common/05-safety_goal.md`
- `references/json-contracts.md`

## 生成方式

所有 Stage 3R review 完成后，先统一运行 `apply_asil_matrix.py` 修正 HARA。然后用工具生成 Stage 4：

```text
python tools/hara/generate_stage4_sg.py --stage-dir output --prefix <run_id> --out output/<run_id>_stage4_sg_sum.json
```

不要手写 `ASIL Level`。例如 `S3+E1+C3` 后缀求和为 `7`，结果是 `A`，不是 `D`。

## 规则

1. 每个 MF 选择最高 ASIL 场景作为 SG_Sum 依据，ASIL 排序为 `QM < A < B < C < D`。
2. `sg_sum` 每行必须包含 `MF_ID`，用于追溯对应功能故障。
3. 如果某个 MF 的最高 ASIL 为 `QM`，该 MF 在 `sg_sum` 中不得出现任何条目；不要生成空白安全目标行，也不要用 `QM` 行占位。
4. 只有最高 ASIL 为 `A/B/C/D` 的 MF 才生成 SG_Sum 条目。
5. 如果多个场景最高 ASIL 相同，选择危害事件和安全目标表达最完整、最能代表该 MF 风险的场景。
6. 安全目标、安全状态和 FTTI 必须来自或符合 Stage 3 已校验场景，不能与故障类型冲突。

Stage 4 写入后，先合并临时 JSON 再检查。若 SG_Sum 的 `ASIL Level` 与 HARA 最高 ASIL 不一致，检查必须失败，不能进入 Stage 4R：

```text
python tools/hara/hara_stage_merge.py --stage-dir output --prefix <run_id> --out output/<run_id>_before_stage4_check.json
python tools/hara/check_stage_json.py --stage stage4 --json output/<run_id>_stage4_sg_sum.json --hara output/<run_id>_before_stage4_check.json --fix
```
