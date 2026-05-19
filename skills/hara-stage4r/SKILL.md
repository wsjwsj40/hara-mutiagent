---
name: hara-stage4r
description: Stage 4R 操作模式评审。用于评审 output/<RUN_ID>_stage4_sg_sum.json 中模型填写的“操作模式”是否具体、与来源 HARA 场景一致；MF 覆盖、QM 过滤、ASIL Level、安全目标、安全状态和 FTTI 主要由 check_stage_json.py 与工具派生保证。
---

# Stage 4R：操作模式评审

## 职责边界

Stage4R 不重建 SG_Sum，也不重新评审安全目标/安全状态语义。确定性字段由工具和 `check_stage_json.py --stage stage4` 保证；Stage4R 只审 `操作模式` 是否合理，并记录最终导出准备状态。

## 输入输出

- 输入：`output/<RUN_ID>_stage4_sg_sum.json`
- 输入：必要时读取对应 `output/<RUN_ID>_stage3_<MF_ID>_hara.json` 的来源场景。
- 输出：`output/<RUN_ID>_stage4_review.json`；如需修正，只更新 Stage4 JSON 的 `操作模式` 字段。

## 上下文加载

1. 先运行 Stage4 机器校验。
2. 读取 `references/stage4-review.md`。
3. 只对报错或有疑问的 `MF_ID` 定向读取 Stage3 HARA 来源行，不加载所有 HARA。

## 检查项

- `操作模式` 不为空、不为占位值。
- `操作模式` 是模式名，不是完整场景描述或长解释。
- `操作模式` 与 `Comments` 中的来源场景、车辆状态和危害事件一致。
- 不改 `MF_ID`、`安全目标`、`ASIL Level`、`安全状态`、`FTTI(ms)`。

## 命令

```text
python tools/hara/hara_stage_merge.py --stage-dir output --prefix <RUN_ID> --out output/<RUN_ID>_before_stage4_check.json

python tools/hara/check_stage_json.py --stage stage4 --json output/<RUN_ID>_stage4_sg_sum.json --hara output/<RUN_ID>_before_stage4_check.json --fix
```

## 返回

返回 `passed/failed`、`total_sg`、操作模式问题数量、修正内容，以及是否允许最终合并导出。
