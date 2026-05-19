---
name: hara-stage4
description: Stage 4 SG_Sum 汇总。用于在 Stage 3 HARA 通过校验后生成 output/<RUN_ID>_stage4_sg_sum.json；除“操作模式”由模型填写外，MF_ID、安全目标、ASIL Level、安全状态、FTTI 和 Comments 都必须由 generate_stage4_sg.py 从 HARA 派生；同一 MF 内相同安全目标汇总时 ASIL 取最高、FTTI 取最小。
---

# Stage 4：SG_Sum 汇总

## 文档分工

- 本文件：定义 Stage4 职责、上下文边界和门禁。
- `references/json-contracts.md`：Stage4 输出结构。
- `references/stage4-sg-summary.md`：工具派生规则和操作模式填写规则。

## 职责边界

Stage4 不是重新生成安全目标。先用 `generate_stage4_sg.py` 从已校验 HARA 派生 SG_Sum 草稿；工具在同一 `MF_ID` 内按相同 `安全目标` 汇总，`ASIL Level` 取该 MF/安全目标组合内的最高值，`FTTI(ms)` 取最小值。不同 MF 即使安全目标文字相同，也分别保留。大模型只填写 `操作模式` 字段，不改 `MF_ID`、`安全目标`、`ASIL Level`、`安全状态`、`FTTI(ms)`、`Comments`、`SG_No`。

## 输入输出

- 输入：所有通过 `check_stage_json.py --stage stage3` 的 `output/<RUN_ID>_stage3_<MF_ID>_hara.json`。
- 输出：`output/<RUN_ID>_stage4_sg_sum.json`。

## 执行流程

1. 运行 `generate_stage4_sg.py` 生成 Stage4 草稿。
2. 只读取 Stage4 草稿里的 `sg_sum` 行和 `Comments` 证据，为每行填写具体 `操作模式`。
3. 不改工具派生字段；如果发现工具派生字段有问题，回到 Stage3 或工具校验修正。
4. 运行 `check_stage_json.py --stage stage4`；若报 `operation_mode_missing_or_placeholder`，只补 `操作模式` 后重跑。

## 操作模式要求

- 写成简洁名词短语，例如：`驻车保持模式`、`坡道起步/低速行驶模式`、`行驶制动控制模式`。
- 依据 `Comments` 中的来源场景证据归纳，不机械复制整段道路/车辆状态。
- 不填写 `nan`、`待填写`、`待补充` 或泛化的 `正常运行模式`。

## 命令

```text
python tools/hara/generate_stage4_sg.py --stage-dir output --prefix <RUN_ID> --out output/<RUN_ID>_stage4_sg_sum.json

python tools/hara/hara_stage_merge.py --stage-dir output --prefix <RUN_ID> --out output/<RUN_ID>_before_stage4_check.json

python tools/hara/check_stage_json.py --stage stage4 --json output/<RUN_ID>_stage4_sg_sum.json --hara output/<RUN_ID>_before_stage4_check.json --fix
```

## 返回

返回 `status`、`total_sg`、待补/已补操作模式数量、输出文件，并说明是否进入 Stage4R。
