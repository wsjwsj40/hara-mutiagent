#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check HARA stage JSON syntax, required fields, and stage count contracts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from hara_schema_columns import DERIVE_MF_COLUMNS, MF_VEHICLE_HAZARDS_COLUMNS, HARA_COLUMNS, SG_SUM_COLUMNS, get_by_alias, is_nan_like, normalize_rows
    from asil_matrix import ASIL_ORDER, normalize_asil
except ImportError:  # pragma: no cover
    from .hara_schema_columns import DERIVE_MF_COLUMNS, MF_VEHICLE_HAZARDS_COLUMNS, HARA_COLUMNS, SG_SUM_COLUMNS, get_by_alias, is_nan_like, normalize_rows
    from .asil_matrix import ASIL_ORDER, normalize_asil

STAGE1_GUIDE_COLUMNS = ["功能丧失", "过大", "过早", "过小", "过晚", "非预期激活", "卡滞", "方向错误"]
STAGE2_TRACE_COLUMNS = ["Function_ID", "source_function_name", "Stage1_Row", "Fault_Field", "Stage1_Fault_Text"]
STAGE3_REVIEW_COLUMNS = [
    "List_No",
    "MF_ID",
    "result",
    "scenario_reality",
    "scenario_independence",
    "internal_consistency",
    "operational_domain_consistency",
    "max_asil_search_coverage",
    "motion_logic",
    "hazard_event_logic",
    "sec_reasoning",
    "safety_goal_consistency",
    "issues",
    "fixes",
    "notes",
]
STAGE3_ENUM_FIELDS = HARA_COLUMNS[4:10]

# Stage 3A scenarios columns (场景字段 + 危害事件 + scenario_reasoning)
SCENARIOS_COLUMNS = [
    "List_No",
    "MF_ID",
    "故障描述",
    "整车危害",
    "道路类型",
    "道路条件",
    "环境条件",
    "车辆状态",
    "车速(km/h)",
    "特殊要素",
    "附加条件",
    "驾驶员是否在车上",
    "危害事件",
    "scenario_reasoning",
]

# Stage 3A/B scenario enum fields (same as Stage 3)
STAGE3A_ENUM_FIELDS = SCENARIOS_COLUMNS[4:10]  # 道路类型 to 特殊要素

# Stage 3B SEC records columns (本阶段生成的 SEC 评级字段)
SEC_RECORDS_COLUMNS = [
    "List_No",
    "E-解释",
    "暴露频率'E'",
    "有风险的人员",
    "可能的后果('S'的理由)",
    "Severity 'S'",
    "C-解释",
    "控制能力 'C'",
    "结果ASIL",
    "sec_reasoning",  # 包含 S评级推理、E评级推理、C评级推理
    "FTTI(ms)",  # 可选
    "备注",  # 可选
]


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise SystemExit(json.dumps({
            "ok": False,
            "file": str(path),
            "error": "json_syntax_error",
            "message": exc.msg,
            "line": exc.lineno,
            "column": exc.colno,
        }, ensure_ascii=False, indent=2))


def dump_json(data: Any, path: Path) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def rows(data: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get(key), list):
        return [item for item in data[key] if isinstance(item, dict)]
    return []


def rows_any(data: Any, *keys: str) -> list[dict[str, Any]]:
    for key in keys:
        found = rows(data, key)
        if found:
            return found
    return []


def missing_fields(row: dict[str, Any], required: list[str]) -> list[str]:
    return [field for field in required if field not in row]


def check_required(rows_: list[dict[str, Any]], required: list[str], sheet: str, errors: list[dict[str, Any]]) -> None:
    for index, row in enumerate(rows_, start=1):
        missing = [field for field in required if get_by_alias(row, field) is None]
        if missing:
            errors.append({
                "stage": sheet,
                "row": index,
                "error": "missing_required_fields",
                "fields": missing,
            })


def check_stage0(data: Any, errors: list[dict[str, Any]]) -> None:
    if not isinstance(data, dict):
        errors.append({"stage": "stage0", "error": "top_level_must_be_object"})
        return
    function_mapping = rows(data, "function_mapping")
    if not function_mapping:
        errors.append({"stage": "stage0", "error": "function_mapping_empty"})
    check_required(function_mapping, ["Function_ID", "extracted_function_name"], "stage0", errors)


def check_stage1(data: Any, stage0: Any | None, errors: list[dict[str, Any]]) -> None:
    derive_mf = rows(data, "derive_mf")
    if not derive_mf:
        errors.append({"stage": "stage1", "error": "derive_mf_empty"})
    check_required(derive_mf, DERIVE_MF_COLUMNS, "stage1", errors)
    if stage0 is not None:
        expected = len(rows(stage0, "function_mapping"))
        if len(derive_mf) != expected:
            errors.append({
                "stage": "stage1",
                "error": "row_count_mismatch",
                "expected_from_stage0": expected,
                "actual": len(derive_mf),
            })


def count_stage1_faults(stage1: Any) -> int:
    return sum(
        1
        for row in rows(stage1, "derive_mf")
        for field in STAGE1_GUIDE_COLUMNS
        if field in row and not is_nan_like(row.get(field))
    )


def check_stage2(data: Any, stage1: Any | None, errors: list[dict[str, Any]], warnings: list[dict[str, Any]] | None = None) -> None:
    hazards = rows(data, "mf_vehicle_hazards")
    if not hazards:
        errors.append({"stage": "stage2", "error": "mf_vehicle_hazards_empty"})
    check_required(hazards, MF_VEHICLE_HAZARDS_COLUMNS, "stage2", errors)
    if warnings is not None:
        for index, row in enumerate(hazards, start=1):
            missing_trace = [field for field in STAGE2_TRACE_COLUMNS if get_by_alias(row, field) is None]
            if missing_trace:
                warnings.append({
                    "stage": "stage2",
                    "row": index,
                    "warning": "stage2_traceability_fields_missing",
                    "fields": missing_trace,
                    "message": "建议补齐 Stage2 追溯字段，便于 Stage3 精确提取 Stage0 detail_text。",
                })
    if stage1 is not None:
        expected = count_stage1_faults(stage1)
        if len(hazards) != expected:
            errors.append({
                "stage": "stage2",
                "error": "row_count_mismatch",
                "expected_from_stage1_non_nan_faults": expected,
                "actual": len(hazards),
            })


def check_stage3(data: Any, min_scenarios: int, max_scenarios: int, mf_id: str | None, errors: list[dict[str, Any]]) -> None:
    hara = rows(data, "hara")
    if len(hara) < min_scenarios or len(hara) > max_scenarios:
        errors.append({
            "stage": "stage3",
            "error": "scenario_count_out_of_range",
            "min": min_scenarios,
            "max": max_scenarios,
            "actual": len(hara),
        })
    check_required(hara, HARA_COLUMNS, "stage3", errors)
    if mf_id:
        other = sorted({str(row.get("MF_ID", "")).strip() for row in hara if str(row.get("MF_ID", "")).strip() != mf_id})
        if other:
            errors.append({
                "stage": "stage3",
                "error": "mixed_mf_id",
                "expected": mf_id,
                "found_other_mf_ids": other,
            })


def check_stage3_against_stage2(data: Any, stage2: Any | None, errors: list[dict[str, Any]]) -> None:
    if stage2 is None:
        return
    hazards = {
        str(row.get("Milf_ID", "")).strip(): row
        for row in rows(stage2, "mf_vehicle_hazards")
        if str(row.get("Milf_ID", "")).strip()
    }
    for index, row in enumerate(rows(data, "hara"), start=1):
        mf_id = str(row.get("MF_ID", "")).strip()
        expected = hazards.get(mf_id)
        if expected is None:
            continue
        expected_fault = str(expected.get("故障描述", "")).strip()
        expected_hazard = str(expected.get("整车级危害", "")).strip()
        actual_fault = str(row.get("故障描述", "")).strip()
        actual_hazard = str(row.get("整车危害", "")).strip()
        if expected_fault and actual_fault != expected_fault:
            errors.append({
                "stage": "stage3",
                "row": index,
                "error": "fault_description_not_verbatim_from_stage2",
                "MF_ID": mf_id,
                "actual": actual_fault,
                "expected": expected_fault,
            })
        if expected_hazard and actual_hazard != expected_hazard:
            errors.append({
                "stage": "stage3",
                "row": index,
                "error": "vehicle_hazard_not_from_stage2",
                "MF_ID": mf_id,
                "actual": actual_hazard,
                "expected": expected_hazard,
            })


def check_stage3_operation_scenarios(data: Any, operation_scenarios: Any | None, errors: list[dict[str, Any]]) -> None:
    if not isinstance(operation_scenarios, dict):
        return
    for index, row in enumerate(rows(data, "hara"), start=1):
        for field in STAGE3_ENUM_FIELDS:
            allowed = operation_scenarios.get(field)
            if not isinstance(allowed, list):
                continue
            value = str(row.get(field, "")).strip()
            if value not in {str(item) for item in allowed}:
                errors.append({
                    "stage": "stage3",
                    "row": index,
                    "error": "scenario_enum_value_not_allowed",
                    "field": field,
                    "value": value,
                    "allowed_source": "operation_scenarios.json",
                })


def check_stage3a(data: Any, min_scenarios: int, max_scenarios: int, mf_id: str | None, errors: list[dict[str, Any]]) -> None:
    """Validate Stage 3A scenarios JSON."""
    if not isinstance(data, dict):
        errors.append({"stage": "stage3a", "error": "top_level_must_be_object"})
        return

    scenarios = rows(data, "scenarios")
    if len(scenarios) < min_scenarios or len(scenarios) > max_scenarios:
        errors.append({
            "stage": "stage3a",
            "error": "scenario_count_out_of_range",
            "min": min_scenarios,
            "max": max_scenarios,
            "actual": len(scenarios),
        })

    check_required(scenarios, SCENARIOS_COLUMNS, "stage3a", errors)

    # Check max_asil_planning exists and is valid
    if "max_asil_planning" not in data:
        errors.append({"stage": "stage3a", "error": "max_asil_planning_missing"})
    else:
        planning = data.get("max_asil_planning")
        if not isinstance(planning, dict):
            errors.append({"stage": "stage3a", "error": "max_asil_planning_must_be_object"})
        else:
            for field in ["高风险因素分析", "规划的场景原型", "预期最大_ASIL", "规划理由"]:
                if field not in planning:
                    errors.append({
                        "stage": "stage3a",
                        "error": "max_asil_planning_missing_field",
                        "field": field,
                    })

    # Check MF_ID consistency
    if mf_id:
        other = sorted({str(row.get("MF_ID", "")).strip() for row in scenarios if str(row.get("MF_ID", "")).strip() != mf_id})
        if other:
            errors.append({
                "stage": "stage3a",
                "error": "mixed_mf_id",
                "expected": mf_id,
                "found_other_mf_ids": other,
            })

    # Check scenario_reasoning structure
    for index, row in enumerate(scenarios, start=1):
        reasoning = row.get("scenario_reasoning")
        if not reasoning or not isinstance(reasoning, dict):
            errors.append({
                "stage": "stage3a",
                "row": index,
                "error": "scenario_reasoning_missing_or_not_object",
            })
            continue
        for field in ["场景规划理由", "危害事件推理", "场景条件相关性检查"]:
            if field not in reasoning:
                errors.append({
                    "stage": "stage3a",
                    "row": index,
                    "error": "scenario_reasoning_missing_field",
                    "field": field,
                })
        # Check 场景条件相关性检查 is an object with 6 condition fields
        conditions = reasoning.get("场景条件相关性检查")
        if not conditions or not isinstance(conditions, dict):
            errors.append({
                "stage": "stage3a",
                "row": index,
                "error": "场景条件相关性检查_missing_or_not_object",
            })
        else:
            for field in ["道路类型", "道路条件", "环境条件", "车辆状态", "车速", "特殊要素"]:
                if field not in conditions:
                    errors.append({
                        "stage": "stage3a",
                        "row": index,
                        "error": "场景条件相关性检查_missing_field",
                        "field": field,
                    })


def check_stage3a_operation_scenarios(data: Any, operation_scenarios: Any | None, errors: list[dict[str, Any]]) -> None:
    """Validate Stage 3A scenario enum fields.

    检查规则：
    1. 每个字段的值必须来自其对应的场景库
    2. 值不能错误地出现在其他字段中（如"泥泞路面"属于"道路条件"，不能放在"特殊要素"中）

    验证前会自动规范化字段值：去除多余空格。规范化后合格则通过。
    """
    if not isinstance(operation_scenarios, dict):
        return

    # 构建值到字段的反向映射，用于检测跨字段误用
    # 同时规范化枚举值（去除多余空格）
    value_to_field: dict[str, str] = {}
    for field_name, allowed_values in operation_scenarios.items():
        if isinstance(allowed_values, list):
            for val in allowed_values:
                val_str = re.sub(r"\s+", "", str(val).strip())  # 规范化枚举值
                if val_str and val_str not in ("ALL", "不涉及"):
                    # 如果值存在于多个字段，记录所有可能
                    if val_str in value_to_field:
                        value_to_field[val_str] += f", {field_name}"
                    else:
                        value_to_field[val_str] = field_name

    for index, row in enumerate(rows(data, "scenarios"), start=1):
        for field in STAGE3A_ENUM_FIELDS:
            allowed = operation_scenarios.get(field)
            if not isinstance(allowed, list):
                continue
            value = str(row.get(field, "")).strip()
            # Allow "不涉及" and "ALL" as special values
            if value in ("不涉及", "ALL", ""):
                continue

            # 规范化：去除内部多余空格
            normalized_value = re.sub(r"\s+", "", value)

            # 构建规范化的允许值集合
            allowed_set = {re.sub(r"\s+", "", str(item).strip()) for item in allowed}

            # 检查规范化后的值是否在允许列表中
            if normalized_value in allowed_set:
                continue  # 规范化后合格，通过

            # 检查值是否属于其他字段（误用检测）
            correct_field = value_to_field.get(normalized_value, "")

            if correct_field:
                # 值确实在场景库中，但用错了字段
                errors.append({
                    "stage": "stage3a",
                    "row": index,
                    "error": "scenario_field_mismatch",
                    "field": field,
                    "value": value,
                    "message": f"值 '{value}' (规范化为 '{normalized_value}') 属于字段 [{correct_field}]，不能用在字段 [{field}] 中",
                    "correct_field": correct_field,
                    "allowed_source": "operation_scenarios.json",
                })
            else:
                # 值根本不在场景库中
                errors.append({
                    "stage": "stage3a",
                    "row": index,
                    "error": "scenario_enum_value_not_in_library",
                    "field": field,
                    "value": value,
                    "message": f"值 '{value}' (规范化为 '{normalized_value}') 不在任何场景库字段中，必须使用 operation_scenarios.json 中定义的值",
                    "allowed_values": sorted(list(allowed_set)),
                    "allowed_source": "operation_scenarios.json",
                })


import re


def normalize_scenario_value(value: str) -> tuple[str, list[str]]:
    """规范化场景字段值，自动修正格式问题。

    返回：(修正后的值, 修正说明列表)

    修正规则：
    1. 去除首尾空格
    2. 中文括号（）转英文括号()
    3. 全角空格转半角空格
    4. 去除内部多余空格
    """
    if not value or not isinstance(value, str):
        return value, []

    original = value
    fixes: list[str] = []

    # 1. 去除首尾空格
    value = value.strip()

    # 2. 中文括号转英文括号（operation_scenarios.json 使用英文括号）
    if "（" in value or "）" in value:
        value = value.replace("（", "(").replace("）", ")")
        fixes.append("中文括号已转为英文括号")

    # 3. 全角空格转半角空格
    if "　" in value:
        value = value.replace("　", " ")
        fixes.append("全角空格已转为半角空格")

    # 4. 去除内部多余空格（将多个连续空格合并为一个）
    collapsed = re.sub(r"\s+", " ", value)
    if collapsed != value:
        value = collapsed
        fixes.append("内部多余空格已合并")

    return value, fixes


def apply_scenario_enum_format_fixes(data: Any, operation_scenarios: Any | None) -> list[dict[str, Any]]:
    """自动修正场景枚举字段的格式问题。

    在验证枚举值之前，先尝试修正格式问题（空格、括号等）。
    只修正简单格式问题，不改变值的语义。
    """
    if not isinstance(operation_scenarios, dict):
        return []

    scenarios = rows(data, "scenarios")
    fixes: list[dict[str, Any]] = []

    # 构建允许值的集合（包含规范化后的版本）
    allowed_sets: dict[str, set[str]] = {}
    for field in STAGE3A_ENUM_FIELDS:
        allowed = operation_scenarios.get(field)
        if isinstance(allowed, list):
            # 同时存储原始值和规范化后的值
            allowed_set = {str(item).strip() for item in allowed}
            normalized_set = set()
            for item in allowed:
                normalized, _ = normalize_scenario_value(str(item))
                normalized_set.add(normalized)
            allowed_sets[field] = allowed_set | normalized_set

    for index, row in enumerate(scenarios, start=1):
        for field in STAGE3A_ENUM_FIELDS:
            current_value = row.get(field, "")
            if not current_value or current_value in ("不涉及", "ALL"):
                continue

            str_value = str(current_value).strip()

            # 尝试规范化
            normalized_value, fix_reasons = normalize_scenario_value(str_value)

            if normalized_value == str_value:
                continue  # 无需修正

            # 检查修正后的值是否在允许列表中
            allowed_set = allowed_sets.get(field, set())
            if normalized_value in allowed_set:
                # 应用修正
                old_value = row[field]
                row[field] = normalized_value
                fixes.append({
                    "stage": "stage3a",
                    "row": index,
                    "field": field,
                    "action": "format_normalized",
                    "old_value": old_value,
                    "new_value": normalized_value,
                    "fixes": fix_reasons,
                })

    return fixes


def apply_scenario_condition_corrections(data: Any, errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """根据 scenario_reasoning 自动修改原字段值为 '不涉及'。

    如果场景条件相关性检查中记录了"不涉及"，自动将原字段值修改为"不涉及"。
    """
    scenarios = rows(data, "scenarios")
    fixes: list[dict[str, Any]] = []
    condition_fields = ["道路类型", "道路条件", "环境条件", "车辆状态", "车速(km/h)", "特殊要素"]

    for index, row in enumerate(scenarios, start=1):
        reasoning = row.get("scenario_reasoning")
        if not reasoning or not isinstance(reasoning, dict):
            continue
        conditions = reasoning.get("场景条件相关性检查")
        if not conditions or not isinstance(conditions, dict):
            continue

        for field in condition_fields:
            reasoning_text = conditions.get(field, "")
            # 检查推理中是否标记为"不涉及"
            if "不涉及" in str(reasoning_text):
                current_value = str(row.get(field, "")).strip()
                if current_value and current_value != "不涉及":
                    # 修改原字段值
                    row[field] = "不涉及"
                    fixes.append({
                        "stage": "stage3a",
                        "row": index,
                        "field": field,
                        "action": "auto_set_to_not_applicable",
                        "old_value": current_value,
                        "new_value": "不涉及",
                        "reasoning": reasoning_text,
                    })

    return fixes


def check_stage3b_raw(data: Any, min_scenarios: int, max_scenarios: int, mf_id: str | None, errors: list[dict[str, Any]]) -> None:
    """Validate Stage 3B raw output (sec_records format).

    Stage 3B 原始输出格式：
    {
      "meta": {...},
      "sec_records": [
        {
          "List_No": 1,
          "E-解释": "...",
          "暴露频率'E'": "E3",
          "有风险的人员": "...",
          "可能的后果('S'的理由)": "...",
          "Severity 'S'": "S1",
          "C-解释": "...",
          "控制能力 'C'": "C2",
          "结果ASIL": "QM (S1+E3+C2=6)",
          "sec_reasoning": {
            "S评级推理": {...},
            "E评级推理": {...},
            "C评级推理": {...}
          },
          "FTTI(ms)": "...",  // 可选
          "备注": "..."  // 可选
        }
      ],
      "safety_goal": "...",
      "safe_state": "..."
    }
    """
    if not isinstance(data, dict):
        errors.append({"stage": "stage3b_raw", "error": "top_level_must_be_object"})
        return

    # Check meta exists
    if "meta" not in data:
        errors.append({"stage": "stage3b_raw", "error": "meta_missing"})
    else:
        meta = data.get("meta")
        if not isinstance(meta, dict):
            errors.append({"stage": "stage3b_raw", "error": "meta_must_be_object"})
        else:
            for field in ["run_id", "mf_id", "stage"]:
                if field not in meta:
                    errors.append({
                        "stage": "stage3b_raw",
                        "error": "meta_missing_field",
                        "field": field,
                    })

    # Check sec_records exists and is an array
    if "sec_records" not in data:
        errors.append({"stage": "stage3b_raw", "error": "sec_records_missing"})
        return

    sec_records = data.get("sec_records")
    if not isinstance(sec_records, list):
        errors.append({"stage": "stage3b_raw", "error": "sec_records_must_be_array"})
        return

    # Check scenario count
    if len(sec_records) < min_scenarios or len(sec_records) > max_scenarios:
        errors.append({
            "stage": "stage3b_raw",
            "error": "sec_records_count_out_of_range",
            "min": min_scenarios,
            "max": max_scenarios,
            "actual": len(sec_records),
        })

    # Check each sec_record has required fields
    required_fields = ["List_No", "E-解释", "暴露频率'E'", "有风险的人员", "可能的后果('S'的理由)",
                       "Severity 'S'", "C-解释", "控制能力 'C'", "结果ASIL", "sec_reasoning"]
    for index, record in enumerate(sec_records, start=1):
        if not isinstance(record, dict):
            errors.append({
                "stage": "stage3b_raw",
                "row": index,
                "error": "sec_record_must_be_object",
            })
            continue

        # Check required fields
        missing = [field for field in required_fields if field not in record]
        if missing:
            errors.append({
                "stage": "stage3b_raw",
                "row": index,
                "error": "sec_record_missing_required_fields",
                "fields": missing,
            })

        # Check sec_reasoning structure
        sec_reasoning = record.get("sec_reasoning")
        if not sec_reasoning or not isinstance(sec_reasoning, dict):
            errors.append({
                "stage": "stage3b_raw",
                "row": index,
                "error": "sec_reasoning_missing_or_not_object",
            })
            continue

        for rating_type in ["S评级推理", "E评级推理", "C评级推理"]:
            if rating_type not in sec_reasoning:
                errors.append({
                    "stage": "stage3b_raw",
                    "row": index,
                    "error": "sec_reasoning_missing_rating",
                    "rating_type": rating_type,
                })

    # Check MF_ID consistency
    if mf_id:
        meta_mf_id = data.get("meta", {}).get("mf_id", "")
        if meta_mf_id != mf_id:
            errors.append({
                "stage": "stage3b_raw",
                "error": "mf_id_mismatch",
                "expected": mf_id,
                "actual": meta_mf_id,
            })
        # Check all sec_records have the same MF_ID (through List_No consistency with stage3a)
        other = sorted({
            str(record.get("MF_ID", "")).strip()
            for record in sec_records
            if isinstance(record, dict) and "MF_ID" in record
        })
        if other and mf_id not in other:
            errors.append({
                "stage": "stage3b_raw",
                "error": "mixed_mf_id",
                "expected": mf_id,
                "found_other_mf_ids": other,
            })

    # Check safety_goal and safe_state (optional but recommended)
    if "safety_goal" not in data:
        errors.append({"stage": "stage3b_raw", "warning": "safety_goal_missing"})
    if "safe_state" not in data:
        errors.append({"stage": "stage3b_raw", "warning": "safe_state_missing"})


def check_stage3b(data: Any, min_scenarios: int, max_scenarios: int, mf_id: str | None, errors: list[dict[str, Any]]) -> None:
    """Validate Stage 3B complete HARA JSON."""
    if not isinstance(data, dict):
        errors.append({"stage": "stage3b", "error": "top_level_must_be_object"})
        return

    # Check that max_asil_planning from Stage 3A is preserved
    if "max_asil_planning" not in data:
        errors.append({"stage": "stage3b", "error": "max_asil_planning_missing_from_stage3a"})

    # Use existing check_stage3 for HARA columns
    check_stage3(data, min_scenarios, max_scenarios, mf_id, errors)

    # Check sec_reasoning exists
    if "sec_reasoning" not in data:
        errors.append({"stage": "stage3b", "error": "sec_reasoning_missing"})
    else:
        sec_reasoning = data.get("sec_reasoning")
        if not isinstance(sec_reasoning, list):
            errors.append({"stage": "stage3b", "error": "sec_reasoning_must_be_array"})
        else:
            # Check each sec_reasoning entry has required fields
            for index, entry in enumerate(sec_reasoning, start=1):
                if not isinstance(entry, dict):
                    continue
                for rating_type in ["S评级推理", "E评级推理", "C评级推理"]:
                    if rating_type not in entry:
                        errors.append({
                            "stage": "stage3b",
                            "row": index,
                            "error": "sec_reasoning_missing_rating",
                            "rating_type": rating_type,
                        })

    # Check that scenario_reasoning from Stage 3A is preserved
    if "scenario_reasoning" not in data:
        errors.append({"stage": "stage3b", "error": "scenario_reasoning_missing_from_stage3a"})
    else:
        scenario_reasoning = data.get("scenario_reasoning")
        if not isinstance(scenario_reasoning, list):
            errors.append({"stage": "stage3b", "error": "scenario_reasoning_must_be_array"})
        else:
            # Check each scenario_reasoning entry has required fields
            for index, entry in enumerate(scenario_reasoning, start=1):
                if not isinstance(entry, dict):
                    continue
                for field in ["场景规划理由", "危害事件推理", "场景条件相关性检查"]:
                    if field not in entry:
                        errors.append({
                            "stage": "stage3b",
                            "row": index,
                            "error": "scenario_reasoning_missing_field",
                            "field": field,
                        })

    # Check that all SEC fields are present (not nan)
    hara = rows(data, "hara")
    for index, row in enumerate(hara, start=1):
        for field in ["Severity 'S'", "暴露频率'E'", "控制能力 'C'", "结果ASIL"]:
            value = row.get(field)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                errors.append({
                    "stage": "stage3b",
                    "row": index,
                    "error": "sec_field_missing_or_empty",
                    "field": field,
                })


def normalize_stage_data(data: Any, stage: str) -> Any:
    if not isinstance(data, dict):
        return data
    normalized = dict(data)
    if stage == "stage1":
        normalized["derive_mf"] = normalize_rows(rows(data, "derive_mf"), DERIVE_MF_COLUMNS)
    elif stage == "stage2":
        source_rows = rows(data, "mf_vehicle_hazards")
        normalized_rows = normalize_rows(source_rows, MF_VEHICLE_HAZARDS_COLUMNS)
        for source_row, normalized_row in zip(source_rows, normalized_rows):
            for key, value in source_row.items():
                if key not in normalized_row:
                    normalized_row[key] = value
        normalized["mf_vehicle_hazards"] = normalized_rows
    elif stage == "stage3":
        normalized["hara"] = normalize_rows(rows(data, "hara"), HARA_COLUMNS)
    elif stage == "stage3a":
        normalized["scenarios"] = normalize_rows(rows(data, "scenarios"), SCENARIOS_COLUMNS)
    elif stage == "stage3b":
        normalized["hara"] = normalize_rows(rows(data, "hara"), HARA_COLUMNS)
    elif stage == "stage4":
        normalized["sg_sum"] = normalize_rows(rows(data, "sg_sum"), SG_SUM_COLUMNS)
    return normalized


def check_stage3_review(data: Any, hara_data: Any | None, mf_id: str | None, errors: list[dict[str, Any]]) -> None:
    if not isinstance(data, dict):
        errors.append({"stage": "stage3_review", "error": "top_level_must_be_object"})
        return

    per_scenario = rows(data, "per_scenario_reviews")
    if not per_scenario:
        if rows(data, "review_results"):
            errors.append({
                "stage": "stage3_review",
                "error": "summary_cannot_replace_per_scenario_review",
                "message": "stage3_review_summary.json 只能作为额外汇总，不能替代每个 MF 的 per_scenario_reviews。",
            })
        else:
            errors.append({
                "stage": "stage3_review",
                "error": "per_scenario_reviews_missing",
            })
        return

    check_required(per_scenario, STAGE3_REVIEW_COLUMNS, "stage3_review", errors)

    if mf_id:
        other = sorted({str(row.get("MF_ID", "")).strip() for row in per_scenario if str(row.get("MF_ID", "")).strip() != mf_id})
        if other:
            errors.append({
                "stage": "stage3_review",
                "error": "mixed_mf_id",
                "expected": mf_id,
                "found_other_mf_ids": other,
            })

    invalid_results = [
        {"row": index, "result": row.get("result")}
        for index, row in enumerate(per_scenario, start=1)
        if str(row.get("result", "")).strip().lower() not in {"pass", "failed"}
    ]
    if invalid_results:
        errors.append({
            "stage": "stage3_review",
            "error": "invalid_review_result",
            "rows": invalid_results,
        })

    if hara_data is None:
        return

    hara_rows = rows(hara_data, "hara")
    if mf_id:
        hara_rows = [row for row in hara_rows if str(row.get("MF_ID", "")).strip() == mf_id]
    expected = {(str(row.get("List_No", "")).strip(), str(row.get("MF_ID", "")).strip()) for row in hara_rows}
    actual = {(str(row.get("List_No", "")).strip(), str(row.get("MF_ID", "")).strip()) for row in per_scenario}
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        errors.append({
            "stage": "stage3_review",
            "error": "missing_scenario_reviews",
            "scenarios": [{"List_No": list_no, "MF_ID": row_mf_id} for list_no, row_mf_id in missing],
        })
    if extra:
        errors.append({
            "stage": "stage3_review",
            "error": "review_references_unknown_scenarios",
            "scenarios": [{"List_No": list_no, "MF_ID": row_mf_id} for list_no, row_mf_id in extra],
        })


def highest_asil_by_mf(hara_rows: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in hara_rows:
        mf_id = str(row.get("MF_ID", "")).strip()
        asil = normalize_asil(row.get("结果ASIL"))
        if not mf_id or asil is None:
            continue
        current = result.get(mf_id)
        if current is None or ASIL_ORDER[asil] > ASIL_ORDER[current]:
            result[mf_id] = asil
    return result


def check_stage4(data: Any, hara_data: Any | None, errors: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> None:
    sg_sum = rows(data, "sg_sum")
    for index, row in enumerate(sg_sum, start=1):
        missing = missing_fields(row, SG_SUM_COLUMNS)
        if missing:
            warnings.append({
                "stage": "stage4",
                "row": index,
                "warning": "missing_required_fields_auto_fixable",
                "fields": missing,
                "message": "最终 validate_hara_json.py 会基于 HARA 最高 ASIL 场景重建或修正 SG_Sum。",
            })
    for index, row in enumerate(sg_sum, start=1):
        asil = normalize_asil(row.get("ASIL Level"))
        if asil is None:
            warnings.append({
                "stage": "stage4",
                "row": index,
                "warning": "sg_asil_level_missing_or_invalid_auto_fixable",
                "value": row.get("ASIL Level"),
            })
        elif asil == "QM":
            warnings.append({
                "stage": "stage4",
                "row": index,
                "warning": "qm_mf_will_be_removed_from_sg_sum",
                "MF_ID": row.get("MF_ID"),
            })

    if hara_data is None:
        return
    mf_highest = highest_asil_by_mf(rows_any(hara_data, "hara", "HARA"))
    expected_non_qm = {mf_id for mf_id, asil in mf_highest.items() if asil != "QM"}
    qm_only = {mf_id for mf_id, asil in mf_highest.items() if asil == "QM"}
    actual = {str(row.get("MF_ID", "")).strip() for row in sg_sum if str(row.get("MF_ID", "")).strip()}
    for index, row in enumerate(sg_sum, start=1):
        mf_id = str(row.get("MF_ID", "")).strip()
        if not mf_id or mf_id not in mf_highest:
            continue
        actual_asil = normalize_asil(row.get("ASIL Level"))
        expected_asil = mf_highest[mf_id]
        if actual_asil != expected_asil:
            errors.append({
                "stage": "stage4",
                "row": index,
                "error": "sg_asil_mismatch_with_hara_highest",
                "MF_ID": mf_id,
                "actual": row.get("ASIL Level"),
                "expected_from_hara": expected_asil,
            })
    missing = sorted(expected_non_qm - actual)
    extra_qm = sorted(qm_only & actual)
    unknown = sorted(actual - set(mf_highest))
    if missing:
        warnings.append({
            "stage": "stage4",
            "warning": "non_qm_mf_missing_sg_sum_entry_auto_fixable",
            "MF_ID": missing,
        })
    if extra_qm:
        warnings.append({
            "stage": "stage4",
            "warning": "qm_mf_will_be_removed_from_sg_sum",
            "MF_ID": extra_qm,
        })
    if unknown:
        warnings.append({
            "stage": "stage4",
            "warning": "sg_sum_references_unknown_mf_will_be_removed",
            "MF_ID": unknown,
        })


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["stage0", "stage1", "stage2", "stage3", "stage3a", "stage3b", "stage3b_raw", "stage3_review", "stage4"], required=True)
    parser.add_argument("--json", required=True)
    parser.add_argument("--stage0")
    parser.add_argument("--stage1")
    parser.add_argument("--stage2")
    parser.add_argument("--hara")
    parser.add_argument("--operation-scenarios")
    parser.add_argument("--mf-id")
    parser.add_argument("--min-scenarios", type=int, default=10)
    parser.add_argument("--max-scenarios", type=int, default=20)
    parser.add_argument("--fix", action="store_true", help="Normalize known stage row keys to canonical schema when validation passes.")
    args = parser.parse_args()

    json_path = Path(args.json)
    data = load_json(json_path)
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if args.stage == "stage0":
        check_stage0(data, errors)
    elif args.stage == "stage1":
        stage0 = load_json(Path(args.stage0)) if args.stage0 else None
        check_stage1(data, stage0, errors)
    elif args.stage == "stage2":
        stage1 = normalize_stage_data(load_json(Path(args.stage1)), "stage1") if args.stage1 else None
        check_stage2(data, stage1, errors, warnings)
    elif args.stage == "stage3":
        check_stage3(data, args.min_scenarios, args.max_scenarios, args.mf_id, errors)
        stage2 = normalize_stage_data(load_json(Path(args.stage2)), "stage2") if args.stage2 else None
        check_stage3_against_stage2(data, stage2, errors)
        operation_scenarios = load_json(Path(args.operation_scenarios)) if args.operation_scenarios else None
        check_stage3_operation_scenarios(data, operation_scenarios, errors)
    elif args.stage == "stage3a":
        check_stage3a(data, args.min_scenarios, args.max_scenarios, args.mf_id, errors)
        operation_scenarios = load_json(Path(args.operation_scenarios)) if args.operation_scenarios else None
        # 自动修正格式问题（空格、括号等）
        format_fixes = apply_scenario_enum_format_fixes(data, operation_scenarios)
        if format_fixes:
            warnings.extend({
                "stage": "stage3a_format_fix",
                "message": f"已自动修正 {len(format_fixes)} 个格式问题（空格、括号等）",
                "fixes": format_fixes,
            } if isinstance(warnings, list) else {"format_fixes": format_fixes})
        check_stage3a_operation_scenarios(data, operation_scenarios, errors)
        # 自动应用"不涉及"修改
        fixes = apply_scenario_condition_corrections(data, errors)
        if fixes:
            warnings.extend({
                "stage": "stage3a_auto_fix",
                "message": f"已根据 scenario_reasoning 自动将 {len(fixes)} 个字段修改为 '不涉及'",
                "fixes": fixes,
            } if isinstance(warnings, list) else {"fixes": fixes})
    elif args.stage == "stage3b":
        check_stage3b(data, args.min_scenarios, args.max_scenarios, args.mf_id, errors)
        operation_scenarios = load_json(Path(args.operation_scenarios)) if args.operation_scenarios else None
        check_stage3_operation_scenarios(data, operation_scenarios, errors)
    elif args.stage == "stage3b_raw":
        check_stage3b_raw(data, args.min_scenarios, args.max_scenarios, args.mf_id, errors)
    elif args.stage == "stage3_review":
        hara_data = normalize_stage_data(load_json(Path(args.hara)), "stage3") if args.hara else None
        check_stage3_review(data, hara_data, args.mf_id, errors)
    elif args.stage == "stage4":
        hara_data = normalize_stage_data(load_json(Path(args.hara)), "stage3") if args.hara else None
        check_stage4(data, hara_data, errors, warnings)

    fixed = False
    if args.fix and not errors and args.stage in {"stage1", "stage2", "stage3", "stage3a", "stage3b", "stage4"}:
        dump_json(normalize_stage_data(data, args.stage), json_path)
        fixed = True

    summary = {
        "ok": not errors,
        "stage": args.stage,
        "file": args.json,
        "fixed": fixed,
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
