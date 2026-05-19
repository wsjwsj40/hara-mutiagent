# Stage 4: SG_Sum 汇总

本文件只定义 Stage4 工具派生和 `操作模式` 填写规则。字段结构见 `json-contracts.md`。

## 派生边界

`generate_stage4_sg.py` 从已通过 Stage3 校验的 HARA 中，在同一 `MF_ID` 内按相同 `安全目标` 汇总非 QM 场景，并派生以下字段：

- `SG_No`
- `MF_ID`
- `安全目标`
- `ASIL Level`
- `安全状态`
- `FTTI(ms)`
- `Comments`

汇总规则：

- 同一 `MF_ID` 内相同 `安全目标` 只生成一条 SG_Sum。
- 不同 `MF_ID` 即使安全目标文字相同，也分别生成 SG_Sum。
- `MF_ID` 保持单个当前 MF，例如 `MF001`。
- `ASIL Level` 取该 MF/安全目标组合内所有非 QM HARA 场景中的最高值。
- `FTTI(ms)` 取该 MF/安全目标组合内所有非 QM HARA 场景中的最小数值。
- `安全状态` 和 `Comments` 由工具从代表场景和分组证据派生。

大模型只填写 `操作模式`。不要让模型重新计算 ASIL、筛选 MF、改写安全目标或安全状态。

## 生成命令

```text
python tools/hara/generate_stage4_sg.py --stage-dir output --prefix <run_id> --out output/<run_id>_stage4_sg_sum.json
```

工具会把 `操作模式` 置为 `待Stage4模型填写`，并在 `Comments` 中写入来源 `List_No` 和场景证据。

## 操作模式填写

根据 `Comments` 中的车辆状态、道路类型、道路条件、驾驶员是否在车上和危害事件，归纳当前安全目标适用的操作模式。

推荐写法：

- `驻车保持模式`
- `坡道起步模式`
- `低速泊车模式`
- `行驶制动控制模式`
- `驾驶员请求驻车/释放模式`

避免写法：

- `待填写`、`nan`
- `正常运行模式`
- 直接复制完整 `Comments`
- 把多个互斥场景堆在一个长句里

## 校验

填写完成后运行：

```text
python tools/hara/hara_stage_merge.py --stage-dir output --prefix <run_id> --out output/<run_id>_before_stage4_check.json
python tools/hara/check_stage_json.py --stage stage4 --json output/<run_id>_stage4_sg_sum.json --hara output/<run_id>_before_stage4_check.json --fix
```

`check_stage_json.py --stage stage4` 会检查：

- 同一 `MF_ID` 内相同 `安全目标` 没有重复 SG_Sum。
- `ASIL Level` 等于该 MF/安全目标组合在 HARA 中的最高 ASIL。
- `FTTI(ms)` 等于该 MF/安全目标组合在 HARA 中的最小 FTTI。
- 非 QM 的 MF/安全目标组合不缺失，QM-only 组合不进入 `sg_sum`。
- `操作模式` 不能是空值或占位值。

最终 `validate_hara_json.py` 会重建派生字段，但会保留已填写的 `操作模式`。
