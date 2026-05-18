# Stage 3BR SEC 评审

本文件只定义 Stage3B SEC 评审。场景生成质量见 `hara-stage3ar`，Stage3A/3B 合并一致性由 `check_stage_json.py --stage stage3` 校验。

## 输出结构

`output/<RUN_ID>_stage3b_<MF_ID>_review.json`

```json
{
  "meta": {
    "run_id": "<RUN_ID>",
    "stage": "stage3b_review",
    "mf_id": "<MF_ID>",
    "target_file": "output/<RUN_ID>_stage3b_<MF_ID>_sec.json",
    "generated_at": "ISO时间戳"
  },
  "overall_result": "pass/failed",
  "issues": [],
  "fixes": [],
  "per_sec_reviews": []
}
```

## 检查点

- S/E/C 是否按事实和知识库规则评级，不为 ASIL 结果倒推。
- `sec_reasoning` 是否充分支持 `Severity 'S'`、`暴露频率'E'`、`控制能力 'C'`。
- `结果ASIL` 是否由机器校验通过；语义评审不手算替代脚本。
- FTTI 是否与危害发展时间、可用反应时间和安全机制需求一致。
- `safety_goal` 是否覆盖当前 MF 最高可信风险路径。
- `safe_state` 是否能实现 `safety_goal`，且与车辆状态一致。

## 修正原则

- 确定性结构和 ASIL 算术问题由 `check_stage_json.py --stage stage3b` 暴露。
- S/E/C 语义错误优先重跑对应维度 batch，不直接手改最终 SEC 文件。
- FTTI 或 safety 问题可修正对应中间文件后重新合并。
