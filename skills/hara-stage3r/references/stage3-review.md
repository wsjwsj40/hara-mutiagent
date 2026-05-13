# Stage 3R: HARA 场景评审

目标：对每个 MF 的 Stage 3 HARA 文件单独评审并修正。Stage 3R 必须发生在 ASIL 工具校验之前。

## 输入

- 当前 MF 的 Stage 3 JSON：`output/<run_id>_stage3_<MF_ID>_hara.json`
- `references/stage3-risk-judgment-rules.md`（详细业务规则）

## 输出

- Review JSON：`output/<run_id>_stage3_<MF_ID>_review.json`
- 修正后的 Stage 3 JSON：仍写回 `output/<run_id>_stage3_<MF_ID>_hara.json`

```json
{
  "meta": {
    "run_id": "<run_id>",
    "stage": "stage3_review",
    "mf_id": "<MF_ID>"
  },
  "per_scenario_reviews": [
    {
      "List_No": "1",
      "MF_ID": "<MF_ID>",
      "result": "pass",
      "format_check": "pass",
      "scenario_quality": "pass",
      "sec_rating": "pass",
      "max_asil_coverage": "pass",
      "issues": [],
      "fixes": [],
      "notes": "评审说明"
    }
  ],
  "review_log": [
    {
      "stage": "stage3_review",
      "target": "<MF_ID>",
      "result": "pass",
      "issues": [],
      "fixes": [],
      "notes": ""
    }
  ]
}
```

`stage3_review_summary.json` 只能作为额外汇总文件，不能替代每个 MF 的 `stage3_<MF_ID>_review.json`，也不能替代 `per_scenario_reviews`。

## 检查点

### A. 格式检查
1. **数量**：10-20 条场景
2. **范围**：只能包含当前 MF 的场景
3. **场景字段**：六大场景字段必须逐字来自 `operation_scenarios.json`，无关条件标记为 `不涉及`

### B. 场景质量检查
4. **现实性**：场景应真实、合理
5. **独立性**：避免核心原型重复（3条以上相同场景应合并）
6. **自洽性**：条件之间不能互相冲突
7. **运行域一致性**：请求相关故障必须在功能运行域内

### C. SEC 评级检查
8. **S/E/C 按事实评级**：不得为了抬高/降低 ASIL 而调整等级
9. **运动逻辑正确**：坡道、运动方向、风险对象位置一致（术语规范见 risk-judgment-rules.md）
10. **解释完整**：E/C 解释必须包含等级定义 + 场景理由
11. **ASIL 算式正确**：S3+E1+C3=7 是 A，不是 D

### D. 最大 ASIL 覆盖检查
12. **优先覆盖高风险原型**：场景不应是随机发散或低风险凑数
13. **限制因素说明**：如果没有 ASIL D，说明是 S/E/C 哪项不足

**详细规则**：S/E/C 判断标准、运动逻辑、术语规范参考 `references/stage3-risk-judgment-rules.md`

## 重要顺序

不要在 Stage 3R 之前运行 `apply_asil_matrix.py`。评审可能会修改 S/E/C、危害事件和安全目标。所有 MF 的 Stage 3R 都通过后，再统一执行 ASIL 校验。

如果发现问题，修改当前 MF 的 Stage 3 JSON，在 review JSON 的 `fixes` 中逐项说明修改原因和修改内容，并在 Stage 3 JSON `review_log` 中记录通过。修正后再次运行 `check_stage_json.py`。

Review JSON 写入后运行：

```text
python tools/hara/check_stage_json.py --stage stage3_review --json output/<run_id>_stage3_<MF_ID>_review.json --hara output/<run_id>_stage3_<MF_ID>_hara.json --mf-id <MF_ID>
```
