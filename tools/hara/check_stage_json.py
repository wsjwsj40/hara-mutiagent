#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check HARA stage JSON syntax, required fields, and stage count contracts."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    from hara_schema_columns import ALIASES, DERIVE_MF_COLUMNS, MF_VEHICLE_HAZARDS_COLUMNS, HARA_COLUMNS, SG_SUM_COLUMNS, get_by_alias, is_nan_like, normalize_rows
    from asil_matrix import ASIL_ORDER, asil_from_sec, normalize_asil, normalize_sec
except ImportError:  # pragma: no cover
    from .hara_schema_columns import ALIASES, DERIVE_MF_COLUMNS, MF_VEHICLE_HAZARDS_COLUMNS, HARA_COLUMNS, SG_SUM_COLUMNS, get_by_alias, is_nan_like, normalize_rows
    from .asil_matrix import ASIL_ORDER, asil_from_sec, normalize_asil, normalize_sec

STAGE1_GUIDE_COLUMNS = ["功能丧失", "过大", "过早", "过小", "过晚", "非预期激活", "卡滞", "方向错误"]
STAGE1_TOP_LEVEL_KEYS = {"meta", "derive_mf", "review_log", "knowledge_evidence", "field_reasoning"}
STAGE1_REASONING_FIELDS = ["功能输出", "异常情况", "后果", "是否适用", "是否有安全风险"]
STAGE1_REASONING_ALIASES = {
    "是否适用": ["是否适合"],
    "是否有安全风险": ["是否有危害", "是否有安全危害"],
}
STAGE1_OPPOSITE_STATE_PAIRS = (
    ("拉起", "释放"),
    ("夹紧", "松开"),
    ("锁止", "解锁"),
    ("上锁", "解锁"),
    ("开启", "关闭"),
    ("打开", "关闭"),
    ("接合", "分离"),
    ("施加", "解除"),
    ("上升", "下降"),
    ("升起", "降下"),
    ("加速", "减速"),
    ("前进", "后退"),
    ("左转", "右转"),
)
STAGE1_MERGED_FAULT_FIELDS = ["过大/过早", "过小/过晚"]
STAGE1_MULTI_EFFECT_MARKERS = ["或", "以及", "同时", "；", ";"]
STAGE2_TRACE_COLUMNS = ["Function_ID", "source_function_name", "Stage1_Row", "Fault_Field", "Stage1_Fault_Text"]
STAGE3_ENUM_FIELDS = HARA_COLUMNS[4:10]
SEC_S_FIELD = "Severity 'S'"
SEC_E_FIELD = "暴露频率'E'"
SEC_C_FIELD = "控制能力 'C'"
ASIL_FIELD = "结果ASIL"

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
STAGE3A_TOP_LEVEL_KEYS = {"meta", "max_asil_planning", "scenarios", "review_log"}
STAGE3A_PLANNING_FIELDS = ["高风险因素分析", "规划的场景原型", "预期最大_ASIL", "规划理由"]
STAGE3A_REASONING_FIELDS = ["场景规划理由", "危害事件推理", "场景条件相关性检查"]
STAGE3A_CONDITION_FIELDS = ["道路类型", "道路条件", "环境条件", "车辆状态", "车速", "特殊要素"]
STAGE3A_CONDITION_TO_SCENARIO_FIELD = {
    "道路类型": "道路类型",
    "道路条件": "道路条件",
    "环境条件": "环境条件",
    "车辆状态": "车辆状态",
    "车速": "车速(km/h)",
    "特殊要素": "特殊要素",
}
STAGE3A_STATIONARY_HOLD_STATES = {"驻车", "停车熄火", "停车未熄火", "泊车", "自动泊车", "启动起步"}
STAGE3A_ROLL_TERMS = ("溜车", "滑动", "滑移", "纵向移动", "前溜", "后溜", "滑行")
STAGE3A_FORWARD_ROLL_TERMS = ("向前滑", "前溜", "向前溜", "前向滑", "向前移动")
STAGE3A_BACKWARD_ROLL_TERMS = ("向后滑", "后溜", "向后溜", "后向滑", "向后移动")
STAGE3A_EPB_HOLD_TERMS = ("EPB", "驻车制动", "静态开关", "拉起", "夹紧力", "夹紧", "无法驻车", "未执行", "无响应")
STAGE3A_SLOPE_TERMS = ("上坡", "下坡", "坡度", "陡坡", "坡道", "斜坡")
STAGE3A_DRIVING_FORCE_TERMS = (
    "D挡",
    "D档",
    "R挡",
    "R档",
    "未挂P",
    "未挂入P",
    "P挡未锁",
    "P档未锁",
    "挡位",
    "档位",
    "蠕行",
    "驱动扭矩",
    "驱动力",
    "牵引力",
    "动力输出",
    "发动机牵引",
    "外力",
    "推动",
    "被推",
    "拖拽",
    "牵引",
)
STAGE3A_WEATHER_OR_VISIBILITY_ENV = ("降雨", "降雪", "冰雹", "雾霾", "沙尘暴", "夜间")
STAGE3A_VISIBILITY_SPECIAL = ("玻璃上起雾", "夜晚路灯条件", "迎面强光")

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
STAGE3B_TOP_LEVEL_KEYS = {"meta", "sec_records", "safety_goal", "safe_state"}
STAGE3B_REQUIRED_FIELDS = [
    "List_No",
    "E-解释",
    "暴露频率'E'",
    "有风险的人员",
    "可能的后果('S'的理由)",
    "Severity 'S'",
    "C-解释",
    "控制能力 'C'",
    "结果ASIL",
    "sec_reasoning",
]
STAGE3B_REASONING_REQUIRED_FIELDS = {
    "S评级推理": ["伤害分析", "碰撞对象", "碰撞速度", "参考规则", "S等级", "S理由"],
    "E评级推理": ["场景持续时间", "场景发生频率", "参考规则", "E等级", "E理由"],
    "C评级推理": ["感知来源", "反应时间", "可用操作", "空间约束", "参考规则", "C等级", "C理由"],
}
STAGE3B_LEVEL_FIELDS = [
    (SEC_S_FIELD, "S评级推理", "S等级", "S"),
    (SEC_E_FIELD, "E评级推理", "E等级", "E"),
    (SEC_C_FIELD, "C评级推理", "C等级", "C"),
]
STAGE3B_FORBIDDEN_RECORD_FIELDS = set(SCENARIOS_COLUMNS) - {"List_No"}
OPERATION_MODE_PLACEHOLDERS = {"待Stage4模型填写", "待填写", "待补充", "待生成", "TODO", "todo"}
WHITESPACE_RE = re.compile(r"[\s\u3000]+")


def normalize_whitespace(value: Any) -> Any:
    """Trim and collapse redundant whitespace without changing JSON shape."""
    if isinstance(value, str):
        return WHITESPACE_RE.sub(" ", value).strip()
    if isinstance(value, list):
        return [normalize_whitespace(item) for item in value]
    if isinstance(value, dict):
        return {
            normalize_whitespace(key) if isinstance(key, str) else key: normalize_whitespace(item)
            for key, item in value.items()
        }
    return value


def compact_text(value: Any) -> str:
    if value is None:
        return ""
    return WHITESPACE_RE.sub("", str(value)).strip()


def text_equal_ignoring_space(left: Any, right: Any) -> bool:
    return compact_text(left) == compact_text(right)


def text_in_ignoring_space(value: Any, choices: set[str]) -> bool:
    normalized = compact_text(value)
    return normalized in {compact_text(choice) for choice in choices}


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
    if isinstance(data, dict):
        value = data.get(key)
        if value is None:
            value = get_by_compact_key(data, key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
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


def top_level_key_diff(data: dict[str, Any], allowed: set[str]) -> tuple[list[str], list[str]]:
    allowed_compact = {compact_field_name(key) for key in allowed}
    actual_compact = {compact_field_name(key) for key in data}
    extra = sorted(key for key in data if compact_field_name(key) not in allowed_compact)
    missing = sorted(key for key in allowed if compact_field_name(key) not in actual_compact)
    return extra, missing


def check_stage0(data: Any, errors: list[dict[str, Any]]) -> None:
    if not isinstance(data, dict):
        errors.append({"stage": "stage0", "error": "top_level_must_be_object"})
        return
    function_mapping = rows(data, "function_mapping")
    if not function_mapping:
        errors.append({"stage": "stage0", "error": "function_mapping_empty"})
    check_required(function_mapping, ["Function_ID", "extracted_function_name"], "stage0", errors)


def compact_field_name(value: Any) -> str:
    return compact_text(value)


def has_compact_key(row: dict[str, Any], expected: str) -> bool:
    expected_compact = compact_field_name(expected)
    return any(compact_field_name(key) == expected_compact for key in row)


def get_by_compact_key(mapping: dict[str, Any], expected: str, default: Any = None) -> Any:
    expected_compact = compact_field_name(expected)
    for key, value in mapping.items():
        if compact_field_name(key) == expected_compact:
            return value
    return default


def stage1_reasoning_candidates(expected: str) -> list[str]:
    return [expected, *STAGE1_REASONING_ALIASES.get(expected, [])]


def has_stage1_reasoning_key(mapping: dict[str, Any], expected: str) -> bool:
    return any(has_compact_key(mapping, candidate) for candidate in stage1_reasoning_candidates(expected))


def get_stage1_reasoning_value(mapping: dict[str, Any], expected: str, default: Any = None) -> Any:
    for candidate in stage1_reasoning_candidates(expected):
        value = get_by_compact_key(mapping, candidate, None)
        if value is not None:
            return value
    return default


def parse_positive_int(value: Any) -> int | None:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def stage0_function_name(row: dict[str, Any]) -> str:
    return str(
        row.get("extracted_function_name")
        or row.get("function_name")
        or row.get("子功能")
        or ""
    ).strip()


def stage0_function_id(row: dict[str, Any]) -> str:
    return str(row.get("Function_ID") or row.get("function_id") or "").strip()


def find_stage0_function(stage0: Any | None, function_id: str | None) -> dict[str, Any] | None:
    if stage0 is None or not function_id:
        return None
    for row in rows(stage0, "function_mapping"):
        if text_equal_ignoring_space(stage0_function_id(row), function_id):
            return row
    return None


def check_stage1_top_level(data: dict[str, Any], errors: list[dict[str, Any]], stage: str = "stage1") -> None:
    extra, missing = top_level_key_diff(data, STAGE1_TOP_LEVEL_KEYS)
    if extra:
        errors.append({
            "stage": stage,
            "error": "unexpected_top_level_keys",
            "keys": extra,
        })
    if missing:
        errors.append({
            "stage": stage,
            "error": "missing_top_level_keys",
            "keys": missing,
        })


def check_stage1_derive_rows(
    derive_mf: list[dict[str, Any]],
    stage0: Any | None,
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]] | None = None,
    auto_fix: bool = False,
    stage: str = "stage1",
) -> None:
    check_required(derive_mf, DERIVE_MF_COLUMNS, stage, errors)
    for index, row in enumerate(derive_mf, start=1):
        for merged_field in STAGE1_MERGED_FAULT_FIELDS:
            if has_compact_key(row, merged_field):
                errors.append({
                    "stage": stage,
                    "row": index,
                    "error": "merged_fault_field_not_allowed",
                    "field": merged_field,
                    "message": "幅值问题和时序问题必须拆开判断，不能使用合并字段。",
                })

        no_value = get_by_alias(row, "No.")
        parsed_no = parse_positive_int(no_value)
        if parsed_no != index:
            errors.append({
                "stage": stage,
                "row": index,
                "error": "no_must_be_consecutive",
                "expected": index,
                "actual": no_value,
            })

        for field in DERIVE_MF_COLUMNS:
            value = get_by_alias(row, field)
            if value is not None and str(value).strip() == "":
                if auto_fix and field in STAGE1_GUIDE_COLUMNS:
                    continue
                errors.append({
                    "stage": stage,
                    "row": index,
                    "error": "field_must_not_be_blank",
                    "field": field,
                    "message": "不适用字段应填写 nan，不能留空。",
                })

        if warnings is not None:
            for field in STAGE1_GUIDE_COLUMNS:
                value = get_by_alias(row, field)
                text = str(value or "").strip()
                if text and not is_nan_like(text) and any(marker in text for marker in STAGE1_MULTI_EFFECT_MARKERS):
                    warnings.append({
                        "stage": stage,
                        "row": index,
                        "field": field,
                        "warning": "possible_multiple_fault_effects_in_one_cell",
                        "message": "每个故障单元格应只描述一个清晰故障效应，请确认没有把多个故障合并在一个字段中。",
                    })

    if stage0 is None:
        return

    function_mapping = rows(stage0, "function_mapping")
    expected = len(function_mapping)
    if len(derive_mf) != expected:
        errors.append({
            "stage": stage,
            "error": "row_count_mismatch",
            "expected_from_stage0": expected,
            "actual": len(derive_mf),
        })
        return

    for index, (stage0_row, stage1_row) in enumerate(zip(function_mapping, derive_mf), start=1):
        expected_name = stage0_function_name(stage0_row)
        actual_name = str(get_by_alias(stage1_row, "子功能") or "").strip()
        if expected_name and not text_equal_ignoring_space(actual_name, expected_name):
            errors.append({
                "stage": stage,
                "row": index,
                "error": "function_name_mismatch_with_stage0",
                "expected": expected_name,
                "actual": actual_name,
            })


def add_stage1_semantic_warnings(
    *,
    stage: str,
    row_no: int,
    function_name: str,
    field: str,
    fault_value: Any,
    applicable: str,
    risk: str,
    warnings: list[dict[str, Any]] | None,
) -> None:
    if warnings is None or is_nan_like(fault_value):
        return

    function_text = compact_text(function_name)
    fault_text = compact_text(fault_value)

    if (
        field == "过大"
        and text_equal_ignoring_space(applicable, "是")
        and text_equal_ignoring_space(risk, "否")
    ):
        no_injury_markers = (
            "不直接造成人身伤害",
            "不会直接造成人身伤害",
            "不直接导致人身伤害",
            "不会直接导致人身伤害",
            "不形成人身伤害风险",
            "无直接人身伤害风险",
            "不直接造成人员伤害",
            "不会直接造成人员伤害",
        )
        if not any(compact_text(marker) in fault_text for marker in no_injury_markers):
            warnings.append({
                "stage": stage,
                "row": row_no,
                "field": field,
                "warning": "stage1_too_much_non_safety_boundary_not_visible",
                "message": "过大故障适用但是否有安全风险=否时，derive_mf 可见描述建议明确不直接造成人身伤害风险，避免后续误入 Stage2。",
            })

    if field == "卡滞":
        for target_state, opposite_state in STAGE1_OPPOSITE_STATE_PAIRS:
            target = compact_text(target_state)
            opposite = compact_text(opposite_state)
            if target not in function_text or opposite in function_text:
                continue
            opposite_direction_markers = (
                f"无法切换到{opposite}",
                f"无法切换至{opposite}",
                f"不能切换到{opposite}",
                f"不能切换至{opposite}",
                f"无法转换到{opposite}",
                f"无法转换至{opposite}",
                f"无法进入{opposite}",
                f"无法完成{opposite}",
                f"{opposite}过程中无法",
                f"{opposite}过程无法",
                f"卡滞在{target}",
                f"卡滞于{target}",
                f"卡滞在已{target}",
                f"卡滞于已{target}",
            )
            if not any(marker in fault_text for marker in opposite_direction_markers):
                continue
            warnings.append({
                "stage": stage,
                "row": row_no,
                "field": field,
                "warning": "stage1_stuck_target_state_direction_suspect",
                "message": f"当前功能目标像是进入“{target_state}”状态，卡滞描述却指向“{opposite_state}”或已处于目标状态后无法退出；请确认是否应改为目标状态无法建立、无法切换到目标状态，或执行过程中无法完成状态切换。",
            })
            break


def check_stage1_field_reasoning(
    data: dict[str, Any],
    derive_mf: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]] | None = None,
    auto_fix: bool = False,
    stage: str = "stage1",
) -> None:
    reasoning = get_by_compact_key(data, "field_reasoning")
    if not isinstance(reasoning, list):
        errors.append({
            "stage": stage,
            "error": "field_reasoning_must_be_array",
        })
        return

    seen_rows: set[int] = set()
    for entry_index, entry in enumerate(reasoning, start=1):
        if not isinstance(entry, dict):
            errors.append({
                "stage": stage,
                "row": entry_index,
                "error": "field_reasoning_entry_must_be_object",
            })
            continue

        row_no = parse_positive_int(get_by_compact_key(entry, "row"))
        if row_no is None or row_no > len(derive_mf):
            errors.append({
                "stage": stage,
                "row": entry_index,
                "error": "field_reasoning_row_invalid",
                "actual": get_by_compact_key(entry, "row"),
            })
            continue
        if row_no in seen_rows:
            errors.append({
                "stage": stage,
                "row": row_no,
                "error": "duplicate_field_reasoning_row",
            })
        seen_rows.add(row_no)

        derive_row = derive_mf[row_no - 1]
        expected_name = str(get_by_alias(derive_row, "子功能") or "").strip()
        actual_name = str(get_by_compact_key(entry, "子功能", "") or "").strip()
        if expected_name and not text_equal_ignoring_space(actual_name, expected_name):
            errors.append({
                "stage": stage,
                "row": row_no,
                "error": "field_reasoning_function_name_mismatch",
                "expected": expected_name,
                "actual": actual_name,
            })

        field_reasoning = get_by_compact_key(entry, "字段推理")
        if not isinstance(field_reasoning, list):
            errors.append({
                "stage": stage,
                "row": row_no,
                "error": "字段推理_must_be_array",
            })
            continue

        seen_fields: set[str] = set()
        for item_index, item in enumerate(field_reasoning, start=1):
            if not isinstance(item, dict):
                errors.append({
                    "stage": stage,
                    "row": row_no,
                    "item": item_index,
                    "error": "field_reasoning_item_must_be_object",
                })
                continue

            field = str(get_by_compact_key(item, "字段", "") or "").strip()
            canonical_field = next(
                (candidate for candidate in STAGE1_GUIDE_COLUMNS if text_equal_ignoring_space(field, candidate)),
                "",
            )
            if not canonical_field:
                errors.append({
                    "stage": stage,
                    "row": row_no,
                    "item": item_index,
                    "error": "invalid_reasoning_field",
                    "field": field,
                    "allowed": STAGE1_GUIDE_COLUMNS,
                })
                continue
            field = canonical_field
            if field in seen_fields:
                errors.append({
                    "stage": stage,
                    "row": row_no,
                    "field": field,
                    "error": "duplicate_reasoning_field",
                })
            seen_fields.add(field)

            inference = get_by_compact_key(item, "推理")
            if not isinstance(inference, dict):
                errors.append({
                    "stage": stage,
                    "row": row_no,
                    "field": field,
                    "error": "推理_must_be_object",
                })
                continue

            missing_reasoning = [
                required
                for required in STAGE1_REASONING_FIELDS
                if not has_stage1_reasoning_key(inference, required)
                or str(get_stage1_reasoning_value(inference, required) or "").strip() == ""
            ]
            if missing_reasoning:
                errors.append({
                    "stage": stage,
                    "row": row_no,
                    "field": field,
                    "error": "reasoning_missing_required_fields",
                    "fields": missing_reasoning,
                })
                continue

            applicable = str(get_stage1_reasoning_value(inference, "是否适用", "") or "").strip()
            if not text_in_ignoring_space(applicable, {"是", "否"}):
                errors.append({
                    "stage": stage,
                    "row": row_no,
                    "field": field,
                    "error": "applicability_flag_must_be_yes_or_no",
                    "actual": applicable,
                })
                continue

            risk = str(get_stage1_reasoning_value(inference, "是否有安全风险", "") or "").strip()
            if not text_in_ignoring_space(risk, {"是", "否"}):
                errors.append({
                    "stage": stage,
                    "row": row_no,
                    "field": field,
                    "error": "risk_flag_must_be_yes_or_no",
                    "actual": risk,
                })
                continue

            if text_equal_ignoring_space(risk, "是") and text_equal_ignoring_space(applicable, "否"):
                errors.append({
                    "stage": stage,
                    "row": row_no,
                    "field": field,
                    "error": "risk_yes_but_applicability_no",
                    "message": "有安全风险的故障必须先是适用的功能故障。",
                })

            fault_value = get_by_alias(derive_row, field)
            if text_equal_ignoring_space(applicable, "是") and is_nan_like(fault_value):
                replacement = str(get_stage1_reasoning_value(inference, "异常情况", "") or "").strip()
                if auto_fix and replacement:
                    derive_row[field] = replacement
                    if warnings is not None:
                        warnings.append({
                            "stage": f"{stage}_auto_fix",
                            "row": row_no,
                            "field": field,
                            "warning": "applicability_yes_fault_nan_replaced_from_reasoning",
                            "old_value": fault_value,
                            "new_value": replacement,
                            "message": "已根据 field_reasoning.推理.异常情况 回填故障字段。",
                        })
                    continue
                errors.append({
                    "stage": stage,
                    "row": row_no,
                    "field": field,
                    "error": "applicability_yes_but_fault_is_nan",
                })
            elif text_equal_ignoring_space(applicable, "否") and not is_nan_like(fault_value):
                if auto_fix:
                    derive_row[field] = "nan"
                    if warnings is not None:
                        warnings.append({
                            "stage": f"{stage}_auto_fix",
                            "row": row_no,
                            "field": field,
                            "warning": "applicability_no_fault_replaced_with_nan",
                            "old_value": fault_value,
                            "new_value": "nan",
                            "message": "已根据 field_reasoning.推理.是否适用=否 将故障字段置为 nan。",
                        })
                    continue
                errors.append({
                    "stage": stage,
                    "row": row_no,
                    "field": field,
                    "error": "applicability_no_but_fault_is_not_nan",
                })

            add_stage1_semantic_warnings(
                stage=stage,
                row_no=row_no,
                function_name=expected_name,
                field=field,
                fault_value=get_by_alias(derive_row, field),
                applicable=applicable,
                risk=risk,
                warnings=warnings,
            )

        missing_fields = [field for field in STAGE1_GUIDE_COLUMNS if field not in seen_fields]
        if missing_fields:
            errors.append({
                "stage": stage,
                "row": row_no,
                "error": "field_reasoning_missing_fault_fields",
                "fields": missing_fields,
            })

    expected_rows = set(range(1, len(derive_mf) + 1))
    missing_rows = sorted(expected_rows - seen_rows)
    if missing_rows:
        errors.append({
            "stage": stage,
            "error": "field_reasoning_missing_rows",
            "rows": missing_rows,
        })


def check_stage1(
    data: Any,
    stage0: Any | None,
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]] | None = None,
    auto_fix: bool = False,
) -> None:
    if not isinstance(data, dict):
        errors.append({"stage": "stage1", "error": "top_level_must_be_object"})
        return
    check_stage1_top_level(data, errors)
    derive_mf = rows(data, "derive_mf")
    if not derive_mf:
        errors.append({"stage": "stage1", "error": "derive_mf_empty"})
        return
    check_stage1_derive_rows(derive_mf, stage0, errors, warnings, auto_fix=auto_fix)
    check_stage1_field_reasoning(data, derive_mf, errors, warnings, auto_fix=auto_fix)


def check_stage1_slice(
    data: Any,
    stage0: Any | None,
    function_id: str | None,
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]] | None = None,
    auto_fix: bool = False,
) -> None:
    if not isinstance(data, dict):
        errors.append({"stage": "stage1_slice", "error": "top_level_must_be_object"})
        return
    check_stage1_top_level(data, errors, stage="stage1_slice")

    derive_mf = rows(data, "derive_mf")
    if len(derive_mf) != 1:
        errors.append({
            "stage": "stage1_slice",
            "error": "stage1_slice_must_have_exactly_one_derive_mf_row",
            "actual": len(derive_mf),
        })
        return

    if rows(data, "field_reasoning") and len(rows(data, "field_reasoning")) != 1:
        errors.append({
            "stage": "stage1_slice",
            "error": "stage1_slice_must_have_exactly_one_field_reasoning_row",
            "actual": len(rows(data, "field_reasoning")),
        })

    meta = get_by_compact_key(data, "meta") if isinstance(get_by_compact_key(data, "meta"), dict) else {}
    meta_function_id = str(get_by_compact_key(meta, "function_id") or get_by_compact_key(meta, "Function_ID") or "").strip()
    effective_function_id = function_id or meta_function_id
    if function_id and meta_function_id and not text_equal_ignoring_space(function_id, meta_function_id):
        errors.append({
            "stage": "stage1_slice",
            "error": "function_id_mismatch_with_meta",
            "expected": function_id,
            "actual": meta_function_id,
        })

    target_stage0_row = find_stage0_function(stage0, effective_function_id)
    if stage0 is not None and effective_function_id and target_stage0_row is None:
        errors.append({
            "stage": "stage1_slice",
            "error": "function_id_not_found_in_stage0",
            "function_id": effective_function_id,
        })

    stage0_slice = {"function_mapping": [target_stage0_row]} if target_stage0_row else None
    check_stage1_derive_rows(derive_mf, stage0_slice, errors, warnings, auto_fix=auto_fix, stage="stage1_slice")
    check_stage1_field_reasoning(data, derive_mf, errors, warnings, auto_fix=auto_fix, stage="stage1_slice")


def stage1_field_reasoning_lookup(stage1: Any) -> dict[tuple[int, str], dict[str, str]]:
    lookup: dict[tuple[int, str], dict[str, str]] = {}
    if not isinstance(stage1, dict):
        return lookup
    for entry in rows(stage1, "field_reasoning"):
        row_no = parse_positive_int(get_by_compact_key(entry, "row"))
        if row_no is None:
            continue
        field_reasoning = get_by_compact_key(entry, "字段推理")
        if not isinstance(field_reasoning, list):
            continue
        for item in field_reasoning:
            if not isinstance(item, dict):
                continue
            field = str(get_by_compact_key(item, "字段", "") or "").strip()
            canonical_field = next(
                (candidate for candidate in STAGE1_GUIDE_COLUMNS if text_equal_ignoring_space(field, candidate)),
                "",
            )
            inference = get_by_compact_key(item, "推理")
            if not canonical_field or not isinstance(inference, dict):
                continue
            lookup[(row_no, canonical_field)] = {
                "是否适用": str(get_stage1_reasoning_value(inference, "是否适用", "") or "").strip(),
                "是否有安全风险": str(get_stage1_reasoning_value(inference, "是否有安全风险", "") or "").strip(),
            }
    return lookup


def expected_stage2_faults(stage1: Any) -> dict[tuple[int, str], Any]:
    """Return Stage1 faults that should be expanded by Stage2.

    Stage1 may contain applicable functional faults that are not safety-relevant.
    Those remain visible in Stage1 but are excluded from Stage2 when
    field_reasoning.推理.是否有安全风险 is explicitly "否".
    """
    lookup = stage1_field_reasoning_lookup(stage1)
    expected: dict[tuple[int, str], Any] = {}
    for row_no, row in enumerate(rows(stage1, "derive_mf"), start=1):
        for field in STAGE1_GUIDE_COLUMNS:
            fault_value = get_by_alias(row, field)
            if is_nan_like(fault_value):
                continue
            reasoning = lookup.get((row_no, field), {})
            risk = reasoning.get("是否有安全风险", "")
            if text_equal_ignoring_space(risk, "否"):
                continue
            expected[(row_no, field)] = fault_value
    return expected


def count_stage1_faults(stage1: Any) -> int:
    return len(expected_stage2_faults(stage1))


def check_stage2_against_stage1_faults(
    hazards: list[dict[str, Any]],
    stage1: Any | None,
    errors: list[dict[str, Any]],
    stage: str,
) -> None:
    if stage1 is None:
        return
    expected = expected_stage2_faults(stage1)
    all_non_nan_faults = {
        (row_no, field): get_by_alias(row, field)
        for row_no, row in enumerate(rows(stage1, "derive_mf"), start=1)
        for field in STAGE1_GUIDE_COLUMNS
        if not is_nan_like(get_by_alias(row, field))
    }
    for index, row in enumerate(hazards, start=1):
        stage1_row = parse_positive_int(get_by_alias(row, "Stage1_Row"))
        fault_field_text = str(get_by_alias(row, "Fault_Field") or "").strip()
        fault_field = next(
            (candidate for candidate in STAGE1_GUIDE_COLUMNS if text_equal_ignoring_space(fault_field_text, candidate)),
            "",
        )
        if stage1_row is None or not fault_field:
            continue
        key = (stage1_row, fault_field)
        if key not in expected:
            error = "stage2_fault_not_safety_relevant" if key in all_non_nan_faults else "stage2_fault_not_found_in_stage1"
            errors.append({
                "stage": stage,
                "row": index,
                "error": error,
                "Stage1_Row": stage1_row,
                "Fault_Field": fault_field_text,
                "message": "Stage2 只能包含 Stage1 中非 nan 且 field_reasoning.推理.是否有安全风险=是 的故障。",
            })
            continue
        stage1_fault_text = str(get_by_alias(row, "Stage1_Fault_Text") or "").strip()
        expected_fault_text = str(expected[key] or "").strip()
        if stage1_fault_text and expected_fault_text and not text_equal_ignoring_space(stage1_fault_text, expected_fault_text):
            errors.append({
                "stage": stage,
                "row": index,
                "error": "stage1_fault_text_mismatch",
                "Stage1_Row": stage1_row,
                "Fault_Field": fault_field_text,
                "expected": expected_fault_text,
                "actual": stage1_fault_text,
            })


def check_stage2(
    data: Any,
    stage1: Any | None,
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]] | None = None,
    stage: str = "stage2",
    allow_empty: bool = False,
) -> None:
    if not isinstance(data, dict):
        errors.append({"stage": stage, "error": "top_level_must_be_object"})
        return
    hazards = rows(data, "mf_vehicle_hazards")
    expected = count_stage1_faults(stage1) if stage1 is not None else None
    if not hazards and not allow_empty and (expected is None or expected > 0):
        errors.append({"stage": stage, "error": "mf_vehicle_hazards_empty"})
    check_required(hazards, MF_VEHICLE_HAZARDS_COLUMNS, stage, errors)

    for index, row in enumerate(hazards, start=1):
        no_value = get_by_alias(row, "No.")
        parsed_no = parse_positive_int(no_value)
        if parsed_no != index:
            errors.append({
                "stage": stage,
                "row": index,
                "error": "no_must_be_consecutive",
                "expected": index,
                "actual": no_value,
            })

    if warnings is not None:
        for index, row in enumerate(hazards, start=1):
            missing_trace = [field for field in STAGE2_TRACE_COLUMNS if get_by_alias(row, field) is None]
            if missing_trace:
                warnings.append({
                    "stage": stage,
                    "row": index,
                    "warning": "stage2_traceability_fields_missing",
                    "fields": missing_trace,
                    "message": "建议补齐 Stage2 追溯字段，便于 Stage3 精确提取 Stage0 detail_text。",
                })

    reasoning = rows(data, "hazard_reasoning")
    if hazards and len(reasoning) != len(hazards):
        errors.append({
            "stage": stage,
            "error": "hazard_reasoning_count_mismatch",
            "expected": len(hazards),
            "actual": len(reasoning),
        })
    for index, (hazard_row, reasoning_row) in enumerate(zip(hazards, reasoning), start=1):
        selected = ""
        inference_value = get_by_compact_key(reasoning_row, "推理")
        inference = inference_value if isinstance(inference_value, dict) else {}
        if isinstance(inference, dict):
            selected = str(get_by_compact_key(inference, "选择的危害", "") or "").strip()
        hazard = str(get_by_alias(hazard_row, "整车级危害") or "").strip()
        if selected and hazard and not text_equal_ignoring_space(selected, hazard):
            errors.append({
                "stage": stage,
                "row": index,
                "error": "hazard_reasoning_selection_mismatch",
                "expected": hazard,
                "actual": selected,
            })

    check_stage2_against_stage1_faults(hazards, stage1, errors, stage)

    if expected is not None:
        if len(hazards) != expected:
            errors.append({
                "stage": stage,
                "error": "row_count_mismatch",
                "expected_from_stage1_safety_relevant_faults": expected,
                "actual": len(hazards),
            })


def check_stage2_slice(
    data: Any,
    stage1: Any | None,
    function_id: str | None,
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]] | None = None,
) -> None:
    if not isinstance(data, dict):
        errors.append({"stage": "stage2_slice", "error": "top_level_must_be_object"})
        return

    meta = get_by_compact_key(data, "meta") if isinstance(get_by_compact_key(data, "meta"), dict) else {}
    meta_function_id = str(get_by_compact_key(meta, "function_id") or get_by_compact_key(meta, "Function_ID") or "").strip()
    effective_function_id = function_id or meta_function_id
    if function_id and meta_function_id and not text_equal_ignoring_space(function_id, meta_function_id):
        errors.append({
            "stage": "stage2_slice",
            "error": "function_id_mismatch_with_meta",
            "expected": function_id,
            "actual": meta_function_id,
        })

    stage1_meta_value = get_by_compact_key(stage1, "meta") if isinstance(stage1, dict) else None
    stage1_meta = stage1_meta_value if isinstance(stage1_meta_value, dict) else {}
    stage1_function_id = str(get_by_compact_key(stage1_meta, "function_id") or get_by_compact_key(stage1_meta, "Function_ID") or "").strip()
    if effective_function_id and stage1_function_id and not text_equal_ignoring_space(effective_function_id, stage1_function_id):
        errors.append({
            "stage": "stage2_slice",
            "error": "function_id_mismatch_with_stage1_slice",
            "expected": effective_function_id,
            "actual": stage1_function_id,
        })

    hazards = rows(data, "mf_vehicle_hazards")
    for index, row in enumerate(hazards, start=1):
        row_function_id = str(get_by_alias(row, "Function_ID") or "").strip()
        if effective_function_id and row_function_id and not text_equal_ignoring_space(row_function_id, effective_function_id):
            errors.append({
                "stage": "stage2_slice",
                "row": index,
                "error": "hazard_function_id_mismatch",
                "expected": effective_function_id,
                "actual": row_function_id,
            })

    check_stage2(data, stage1, errors, warnings, stage="stage2_slice", allow_empty=True)


def check_asil_consistency(
    row: dict[str, Any],
    stage: str,
    index: int,
    errors: list[dict[str, Any]],
) -> tuple[str | None, str | None]:
    expected_asil = asil_from_sec(
        get_by_compact_key(row, SEC_S_FIELD),
        get_by_compact_key(row, SEC_E_FIELD),
        get_by_compact_key(row, SEC_C_FIELD),
    )
    actual_asil = normalize_asil(get_by_compact_key(row, ASIL_FIELD))
    if expected_asil is None:
        errors.append({
            "stage": stage,
            "row": index,
            "error": "asil_cannot_be_calculated_from_sec",
            "S": get_by_compact_key(row, SEC_S_FIELD),
            "E": get_by_compact_key(row, SEC_E_FIELD),
            "C": get_by_compact_key(row, SEC_C_FIELD),
        })
    elif actual_asil != expected_asil:
        errors.append({
            "stage": stage,
            "row": index,
            "error": "asil_mismatch_with_sec",
            "expected": expected_asil,
            "actual": get_by_compact_key(row, ASIL_FIELD),
        })
    return expected_asil, actual_asil


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
    for index, row in enumerate(hara, start=1):
        check_asil_consistency(row, "stage3", index, errors)
    if mf_id:
        other = sorted({
            str(row.get("MF_ID", "")).strip()
            for row in hara
            if str(row.get("MF_ID", "")).strip()
            and not text_equal_ignoring_space(row.get("MF_ID"), mf_id)
        })
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
        compact_text(row.get("Milf_ID")): row
        for row in rows(stage2, "mf_vehicle_hazards")
        if compact_text(row.get("Milf_ID"))
    }
    for index, row in enumerate(rows(data, "hara"), start=1):
        mf_id = str(row.get("MF_ID", "")).strip()
        expected = hazards.get(compact_text(mf_id))
        if expected is None:
            continue
        expected_fault = str(expected.get("故障描述", "")).strip()
        expected_hazard = str(expected.get("整车级危害", "")).strip()
        actual_fault = str(row.get("故障描述", "")).strip()
        actual_hazard = str(row.get("整车危害", "")).strip()
        if expected_fault and not text_equal_ignoring_space(actual_fault, expected_fault):
            errors.append({
                "stage": "stage3",
                "row": index,
                "error": "fault_description_not_verbatim_from_stage2",
                "MF_ID": mf_id,
                "actual": actual_fault,
                "expected": expected_fault,
            })
        if expected_hazard and not text_equal_ignoring_space(actual_hazard, expected_hazard):
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
            if not text_in_ignoring_space(value, {str(item) for item in allowed}):
                errors.append({
                    "stage": "stage3",
                    "row": index,
                    "error": "scenario_enum_value_not_allowed",
                    "field": field,
                    "value": value,
                    "allowed_source": "operation_scenarios.json",
                })


def stage2_mf_lookup(stage2: Any | None) -> dict[str, dict[str, Any]]:
    if stage2 is None:
        return {}
    return {
        compact_text(get_by_alias(row, "Milf_ID")): row
        for row in rows(stage2, "mf_vehicle_hazards")
        if compact_text(get_by_alias(row, "Milf_ID"))
    }


def condition_is_not_applicable(value: Any) -> bool:
    return compact_text(value).startswith(compact_text("不涉及"))


def condition_is_related(value: Any) -> bool:
    return compact_text(value).startswith(compact_text("相关"))


def contains_any(text: str, terms: tuple[str, ...] | set[str]) -> bool:
    return any(compact_text(term) in text for term in terms)


def compact_join(values: list[Any]) -> str:
    return compact_text(" ".join(str(value) for value in values if value is not None))


def scenario_reasoning_text(row: dict[str, Any]) -> str:
    return compact_text(get_by_compact_key(row, "scenario_reasoning") or "")


def stage3a_condition_reasoning(row: dict[str, Any], field: str) -> str:
    reasoning = get_by_compact_key(row, "scenario_reasoning")
    if not isinstance(reasoning, dict):
        return ""
    conditions = get_by_compact_key(reasoning, "场景条件相关性检查")
    if not isinstance(conditions, dict):
        return ""
    return str(get_by_compact_key(conditions, field, "") or "").strip()


def is_stage3a_slope_road(road_condition: Any) -> bool:
    return text_in_ignoring_space(road_condition, {"上坡道路", "下坡道路"})


def check_stage3a_semantic_logic(scenarios: list[dict[str, Any]], errors: list[dict[str, Any]]) -> None:
    """Catch high-confidence Stage 3A scene logic errors.

    This intentionally stays heuristic: it blocks contradictions that should be
    fixed before SEC rating, while leaving nuanced risk-rating judgment to Stage3B.
    """
    for index, row in enumerate(scenarios, start=1):
        row_no = get_by_alias(row, "List_No") or index
        road_condition = str(get_by_alias(row, "道路条件") or "").strip()
        environment = str(get_by_alias(row, "环境条件") or "").strip()
        vehicle_state = str(get_by_alias(row, "车辆状态") or "").strip()
        speed = str(get_by_alias(row, "车速(km/h)") or "").strip()
        special = str(get_by_alias(row, "特殊要素") or "").strip()
        additional = str(get_by_alias(row, "附加条件") or "").strip()
        hazard_event = str(get_by_alias(row, "危害事件") or "").strip()
        fault = str(get_by_alias(row, "故障描述") or "").strip()
        vehicle_hazard = str(get_by_alias(row, "整车危害") or "").strip()
        reasoning = scenario_reasoning_text(row)

        condition_text = compact_join([additional, hazard_event, reasoning])
        causal_text = compact_join([fault, vehicle_hazard, hazard_event, reasoning])
        fault_text = compact_text(fault)
        hazard_text = compact_text(hazard_event)
        additional_text = compact_text(additional)

        has_roll_hazard = contains_any(causal_text, STAGE3A_ROLL_TERMS)
        is_stationary_hold = (
            text_in_ignoring_space(vehicle_state, STAGE3A_STATIONARY_HOLD_STATES)
            or text_equal_ignoring_space(speed, "静止状态")
        )
        is_epb_hold_fault = contains_any(fault_text, STAGE3A_EPB_HOLD_TERMS)
        has_slope_text = contains_any(condition_text, STAGE3A_SLOPE_TERMS) or bool(
            re.search(r"\d+(?:\.\d+)?%", condition_text)
        )
        has_slope_road = is_stage3a_slope_road(road_condition)
        has_drive_or_external_force = contains_any(condition_text, STAGE3A_DRIVING_FORCE_TERMS)

        if has_slope_text and not has_slope_road:
            errors.append({
                "stage": "stage3a",
                "row": index,
                "List_No": row_no,
                "error": "slope_text_requires_slope_road_condition",
                "road_condition": road_condition,
                "message": "附加条件、危害事件或推理中出现上坡/下坡/坡度/陡坡时，道路条件必须选择 上坡道路 或 下坡道路，不能选择直道或普通路面枚举。",
            })

        if text_equal_ignoring_space(road_condition, "上坡道路") and contains_any(condition_text, STAGE3A_FORWARD_ROLL_TERMS):
            errors.append({
                "stage": "stage3a",
                "row": index,
                "List_No": row_no,
                "error": "uphill_roll_direction_must_be_backward",
                "message": "按 Stage3A 车辆动力学规则，上坡道路溜车方向应为向后，不能写成向前滑动。",
            })

        if text_equal_ignoring_space(road_condition, "下坡道路") and contains_any(condition_text, STAGE3A_BACKWARD_ROLL_TERMS):
            errors.append({
                "stage": "stage3a",
                "row": index,
                "List_No": row_no,
                "error": "downhill_roll_direction_must_be_forward",
                "message": "按 Stage3A 车辆动力学规则，下坡道路溜车方向应为向前，不能写成向后滑动。",
            })

        if has_roll_hazard and is_stationary_hold and not (has_slope_road or has_slope_text or has_drive_or_external_force):
            errors.append({
                "stage": "stage3a",
                "row": index,
                "List_No": row_no,
                "error": "stationary_longitudinal_movement_lacks_force_source",
                "vehicle_state": vehicle_state,
                "speed": speed,
                "road_condition": road_condition,
                "message": "驻车/停车/静止场景发生非预期纵向移动时，必须说明坡道重力、D/R挡蠕行、未挂P挡、外力推动等实际纵向力来源；低附着、天气或前车距离不能单独导致当前 MF 的溜车危害。",
            })

        collides_with_front_vehicle = (
            "与前车" in hazard_text
            or "前车发生" in hazard_text
            or "前方停放车辆" in hazard_text
            or ("前方" in additional_text and ("停放车辆" in additional_text or "前车" in additional_text))
        )
        collides_with_oncoming = (
            "与对向车辆" in hazard_text
            or "与对向来车" in hazard_text
            or "对向来车" in additional_text
            or text_equal_ignoring_space(special, "与对向来车距离较近")
        )
        if "对向车辆乘员" in hazard_text and collides_with_front_vehicle and not collides_with_oncoming:
            errors.append({
                "stage": "stage3a",
                "row": index,
                "List_No": row_no,
                "error": "risk_object_conflicts_with_front_vehicle_collision",
                "message": "危害事件写了对向车辆乘员，但附加条件/碰撞对象是前车或前方停放车辆；风险对象应与碰撞对象一致。",
            })
        if ("前车乘员" in hazard_text or "前方车辆乘员" in hazard_text) and collides_with_oncoming and not collides_with_front_vehicle:
            errors.append({
                "stage": "stage3a",
                "row": index,
                "List_No": row_no,
                "error": "risk_object_conflicts_with_oncoming_collision",
                "message": "危害事件写了前车/前方车辆乘员，但场景对象是对向来车；风险对象应与碰撞对象一致。",
            })

        if is_epb_hold_fault and has_roll_hazard and is_stationary_hold:
            env_reasoning = stage3a_condition_reasoning(row, "环境条件")
            if environment and not text_in_ignoring_space(environment, {"不涉及", "ALL", "日间"}) and condition_is_related(env_reasoning):
                is_wind_push = ("大风" in compact_text(environment) or "强侧面风" in compact_text(environment)) and contains_any(condition_text, {"推动", "外力"})
                if not is_wind_push and contains_any(compact_text(environment), STAGE3A_WEATHER_OR_VISIBILITY_ENV):
                    errors.append({
                        "stage": "stage3a",
                        "row": index,
                        "List_No": row_no,
                        "error": "epb_roll_environment_marked_related_without_causal_role",
                        "environment": environment,
                        "message": "EPB/驻车保持类溜车场景中，天气/能见度不能替代故障因果；若只影响暴露或可控性，应在 Stage3A 标为 不涉及。",
                    })

            special_reasoning = stage3a_condition_reasoning(row, "特殊要素")
            if special and condition_is_related(special_reasoning) and contains_any(compact_text(special), STAGE3A_VISIBILITY_SPECIAL):
                errors.append({
                    "stage": "stage3a",
                    "row": index,
                    "List_No": row_no,
                    "error": "epb_roll_visibility_special_marked_related_without_causal_role",
                    "special": special,
                    "message": "玻璃起雾、路灯、强光等视野条件不改变 EPB 驻车溜车的发生链路；若只影响驾驶员感知或可控性，应标为 不涉及。",
                })


def check_stage3a_top_level(data: dict[str, Any], errors: list[dict[str, Any]]) -> None:
    extra, missing = top_level_key_diff(data, STAGE3A_TOP_LEVEL_KEYS)
    if extra:
        errors.append({"stage": "stage3a", "error": "unexpected_top_level_keys", "keys": extra})
    if missing:
        errors.append({"stage": "stage3a", "error": "missing_top_level_keys", "keys": missing})


def check_stage3a_meta(data: dict[str, Any], mf_id: str | None, errors: list[dict[str, Any]]) -> None:
    meta = get_by_compact_key(data, "meta")
    if not isinstance(meta, dict):
        errors.append({"stage": "stage3a", "error": "meta_must_be_object"})
        return
    if not text_equal_ignoring_space(get_by_compact_key(meta, "stage"), "stage3a"):
        errors.append({
            "stage": "stage3a",
            "error": "meta_stage_must_be_stage3a",
            "actual": get_by_compact_key(meta, "stage"),
        })
    meta_mf_id = str(get_by_compact_key(meta, "mf_id") or get_by_compact_key(meta, "MF_ID") or "").strip()
    if not meta_mf_id:
        errors.append({"stage": "stage3a", "error": "meta_mf_id_required"})
    elif mf_id and not text_equal_ignoring_space(meta_mf_id, mf_id):
        errors.append({
            "stage": "stage3a",
            "error": "mf_id_mismatch_with_meta",
            "expected": mf_id,
            "actual": meta_mf_id,
        })


def stage3a_effective_mf_id(data: dict[str, Any], mf_id: str | None) -> str | None:
    if mf_id:
        return mf_id
    meta = get_by_compact_key(data, "meta")
    if not isinstance(meta, dict):
        return None
    meta_mf_id = str(get_by_compact_key(meta, "mf_id") or get_by_compact_key(meta, "MF_ID") or "").strip()
    return meta_mf_id or None


def check_stage3a_against_stage2(
    scenarios: list[dict[str, Any]],
    stage2: Any | None,
    mf_id: str | None,
    errors: list[dict[str, Any]],
) -> None:
    if stage2 is None or not mf_id:
        return
    expected = stage2_mf_lookup(stage2).get(compact_text(mf_id))
    if expected is None:
        errors.append({"stage": "stage3a", "error": "mf_id_not_found_in_stage2", "MF_ID": mf_id})
        return
    expected_fault = str(get_by_alias(expected, "故障描述") or "").strip()
    expected_hazard = str(get_by_alias(expected, "整车级危害") or "").strip()
    for index, row in enumerate(scenarios, start=1):
        actual_fault = str(get_by_alias(row, "故障描述") or "").strip()
        actual_hazard = str(get_by_alias(row, "整车危害") or "").strip()
        if expected_fault and not text_equal_ignoring_space(actual_fault, expected_fault):
            errors.append({
                "stage": "stage3a",
                "row": index,
                "error": "fault_description_not_verbatim_from_stage2",
                "MF_ID": mf_id,
                "expected": expected_fault,
                "actual": actual_fault,
            })
        if expected_hazard and not text_equal_ignoring_space(actual_hazard, expected_hazard):
            errors.append({
                "stage": "stage3a",
                "row": index,
                "error": "vehicle_hazard_not_from_stage2",
                "MF_ID": mf_id,
                "expected": expected_hazard,
                "actual": actual_hazard,
            })


def check_stage3a_condition_consistency(
    scenarios: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> None:
    for index, row in enumerate(scenarios, start=1):
        reasoning = get_by_compact_key(row, "scenario_reasoning")
        if not isinstance(reasoning, dict):
            continue
        conditions = get_by_compact_key(reasoning, "场景条件相关性检查")
        if not isinstance(conditions, dict):
            continue
        for condition_field, scenario_field in STAGE3A_CONDITION_TO_SCENARIO_FIELD.items():
            reasoning_text = str(get_by_compact_key(conditions, condition_field, "")).strip()
            if not reasoning_text:
                continue
            scenario_value = str(get_by_alias(row, scenario_field) or "").strip()
            if not (condition_is_not_applicable(reasoning_text) or condition_is_related(reasoning_text)):
                errors.append({
                    "stage": "stage3a",
                    "row": index,
                    "error": "condition_relevance_must_start_with_related_or_not_applicable",
                    "field": condition_field,
                    "actual": reasoning_text,
                })
            if condition_is_not_applicable(reasoning_text) and not text_equal_ignoring_space(scenario_value, "不涉及"):
                errors.append({
                    "stage": "stage3a",
                    "row": index,
                    "error": "condition_marked_not_applicable_but_field_not_fixed",
                    "field": scenario_field,
                    "actual": scenario_value,
                    "message": "该字段推理标记为不涉及，运行 --fix 可将场景字段规范化为 不涉及。",
                })
            if text_equal_ignoring_space(scenario_value, "不涉及") and not condition_is_not_applicable(reasoning_text):
                errors.append({
                    "stage": "stage3a",
                    "row": index,
                    "error": "field_not_applicable_but_reasoning_not_marked",
                    "field": scenario_field,
                    "reasoning_field": condition_field,
                    "actual_reasoning": reasoning_text,
                })


def check_stage3a(
    data: Any,
    min_scenarios: int,
    max_scenarios: int,
    mf_id: str | None,
    errors: list[dict[str, Any]],
    stage2: Any | None = None,
) -> None:
    """Validate Stage 3A scenarios JSON."""
    if not isinstance(data, dict):
        errors.append({"stage": "stage3a", "error": "top_level_must_be_object"})
        return
    check_stage3a_top_level(data, errors)
    check_stage3a_meta(data, mf_id, errors)
    effective_mf_id = stage3a_effective_mf_id(data, mf_id)

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

    if not has_compact_key(data, "max_asil_planning"):
        errors.append({"stage": "stage3a", "error": "max_asil_planning_missing"})
    else:
        planning = get_by_compact_key(data, "max_asil_planning")
        if not isinstance(planning, dict):
            errors.append({"stage": "stage3a", "error": "max_asil_planning_must_be_object"})
        else:
            for field in STAGE3A_PLANNING_FIELDS:
                value = get_by_compact_key(planning, field)
                if not has_compact_key(planning, field):
                    errors.append({
                        "stage": "stage3a",
                        "error": "max_asil_planning_missing_field",
                        "field": field,
                    })
                elif isinstance(value, list) and not value:
                    errors.append({
                        "stage": "stage3a",
                        "error": "max_asil_planning_field_must_not_be_empty",
                        "field": field,
                    })
                elif not isinstance(value, list) and not str(value or "").strip():
                    errors.append({
                        "stage": "stage3a",
                        "error": "max_asil_planning_field_must_not_be_blank",
                        "field": field,
                    })

    if effective_mf_id:
        other = sorted({
            str(row.get("MF_ID", "")).strip()
            for row in scenarios
            if str(row.get("MF_ID", "")).strip()
            and not text_equal_ignoring_space(row.get("MF_ID"), effective_mf_id)
        })
        if other:
            errors.append({
                "stage": "stage3a",
                "error": "mixed_mf_id",
                "expected": effective_mf_id,
                "found_other_mf_ids": other,
            })

    for index, row in enumerate(scenarios, start=1):
        list_no = parse_positive_int(get_by_alias(row, "List_No"))
        if list_no != index:
            errors.append({
                "stage": "stage3a",
                "row": index,
                "error": "list_no_must_be_consecutive",
                "expected": index,
                "actual": get_by_alias(row, "List_No"),
            })

        driver_present = str(get_by_alias(row, "驾驶员是否在车上") or "").strip()
        if driver_present and not text_in_ignoring_space(driver_present, {"是", "否", "不涉及"}):
            errors.append({
                "stage": "stage3a",
                "row": index,
                "error": "driver_present_must_be_yes_no_or_not_applicable",
                "actual": driver_present,
            })

        reasoning = get_by_compact_key(row, "scenario_reasoning")
        if not reasoning or not isinstance(reasoning, dict):
            errors.append({
                "stage": "stage3a",
                "row": index,
                "error": "scenario_reasoning_missing_or_not_object",
            })
            continue
        for field in STAGE3A_REASONING_FIELDS:
            if not has_compact_key(reasoning, field) or (
                field != "场景条件相关性检查" and not str(get_by_compact_key(reasoning, field) or "").strip()
            ):
                errors.append({
                    "stage": "stage3a",
                    "row": index,
                    "error": "scenario_reasoning_missing_field",
                    "field": field,
                })
        conditions = get_by_compact_key(reasoning, "场景条件相关性检查")
        if not conditions or not isinstance(conditions, dict):
            errors.append({
                "stage": "stage3a",
                "row": index,
                "error": "场景条件相关性检查_missing_or_not_object",
            })
        else:
            for field in STAGE3A_CONDITION_FIELDS:
                if not has_compact_key(conditions, field) or not str(get_by_compact_key(conditions, field) or "").strip():
                    errors.append({
                        "stage": "stage3a",
                        "row": index,
                        "error": "场景条件相关性检查_missing_field",
                        "field": field,
                    })
    check_stage3a_semantic_logic(scenarios, errors)
    check_stage3a_against_stage2(scenarios, stage2, effective_mf_id, errors)


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
                if val_str and not text_in_ignoring_space(val_str, {"ALL", "不涉及"}):
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
            if not value or text_in_ignoring_space(value, {"不涉及", "ALL"}):
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
    allowed_maps: dict[str, dict[str, str]] = {}
    for field in STAGE3A_ENUM_FIELDS:
        allowed = operation_scenarios.get(field)
        if isinstance(allowed, list):
            # Store canonical enum values by their whitespace-insensitive key.
            allowed_map: dict[str, str] = {}
            for item in allowed:
                canonical = str(item).strip()
                normalized, _ = normalize_scenario_value(str(item))
                for candidate in {canonical, normalized}:
                    if candidate:
                        allowed_map[compact_text(candidate)] = canonical
            allowed_maps[field] = allowed_map

    for index, row in enumerate(scenarios, start=1):
        for field in STAGE3A_ENUM_FIELDS:
            current_value = row.get(field, "")
            if not current_value or text_in_ignoring_space(current_value, {"不涉及", "ALL"}):
                continue

            str_value = str(current_value).strip()

            # 尝试规范化
            normalized_value, fix_reasons = normalize_scenario_value(str_value)

            allowed_map = allowed_maps.get(field, {})
            canonical_value = allowed_map.get(compact_text(normalized_value))
            if canonical_value and canonical_value != str_value:
                old_value = row[field]
                row[field] = canonical_value
                if not fix_reasons:
                    fix_reasons = ["多余空格已移除"]
                fixes.append({
                    "stage": "stage3a",
                    "row": index,
                    "field": field,
                    "action": "format_normalized",
                    "old_value": old_value,
                    "new_value": canonical_value,
                    "fixes": fix_reasons,
                })

    return fixes


def apply_scenario_condition_corrections(data: Any) -> list[dict[str, Any]]:
    """根据 scenario_reasoning 自动修改原字段值为 '不涉及'。

    如果场景条件相关性检查中记录了"不涉及"，自动将原字段值修改为"不涉及"。
    """
    scenarios = rows(data, "scenarios")
    fixes: list[dict[str, Any]] = []

    for index, row in enumerate(scenarios, start=1):
        reasoning = get_by_compact_key(row, "scenario_reasoning")
        if not reasoning or not isinstance(reasoning, dict):
            continue
        conditions = get_by_compact_key(reasoning, "场景条件相关性检查")
        if not conditions or not isinstance(conditions, dict):
            continue

        for condition_field, scenario_field in STAGE3A_CONDITION_TO_SCENARIO_FIELD.items():
            reasoning_text = get_by_compact_key(conditions, condition_field, "")
            # 检查推理中是否标记为"不涉及"
            if condition_is_not_applicable(reasoning_text):
                current_value = str(get_by_alias(row, scenario_field) or "").strip()
                if current_value and not text_equal_ignoring_space(current_value, "不涉及"):
                    # 修改原字段值
                    row[scenario_field] = "不涉及"
                    fixes.append({
                        "stage": "stage3a",
                        "row": index,
                        "field": scenario_field,
                        "reasoning_field": condition_field,
                        "action": "auto_set_to_not_applicable",
                        "old_value": current_value,
                        "new_value": "不涉及",
                        "reasoning": reasoning_text,
                    })

    return fixes


def is_blankish(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        text = value.strip()
        return text == "" or is_nan_like(text)
    return False


def stage3b_effective_mf_id(data: dict[str, Any], mf_id: str | None) -> str | None:
    if mf_id:
        return mf_id
    meta = get_by_compact_key(data, "meta")
    if not isinstance(meta, dict):
        return None
    meta_mf_id = str(get_by_compact_key(meta, "mf_id") or get_by_compact_key(meta, "MF_ID") or "").strip()
    return meta_mf_id or None


def check_stage3b_top_level(data: dict[str, Any], errors: list[dict[str, Any]]) -> None:
    extra, missing = top_level_key_diff(data, STAGE3B_TOP_LEVEL_KEYS)
    if extra:
        errors.append({"stage": "stage3b", "error": "unexpected_top_level_keys", "keys": extra})
    if missing:
        errors.append({"stage": "stage3b", "error": "missing_top_level_keys", "keys": missing})


def sec_formula_fragment(s_level: str, e_level: str, c_level: str) -> str:
    total = int(s_level[1:]) + int(e_level[1:]) + int(c_level[1:])
    return f"{s_level}+{e_level}+{c_level}={total}"


def ftti_is_numeric(value: Any) -> bool:
    text = str(value).strip()
    if text == "":
        return False
    try:
        return float(text) >= 0
    except ValueError:
        return False


def check_stage3b_against_stage3a(
    sec_records: list[dict[str, Any]],
    stage3a: Any | None,
    mf_id: str | None,
    errors: list[dict[str, Any]],
) -> None:
    if stage3a is None:
        return
    if not isinstance(stage3a, dict):
        errors.append({"stage": "stage3b", "error": "stage3a_must_be_object"})
        return
    scenarios = rows(stage3a, "scenarios")
    expected_list_nos = [parse_positive_int(get_by_alias(row, "List_No")) for row in scenarios]
    actual_list_nos = [parse_positive_int(get_by_alias(row, "List_No")) for row in sec_records]
    if len(sec_records) != len(scenarios):
        errors.append({
            "stage": "stage3b",
            "error": "sec_record_count_mismatch_with_stage3a",
            "expected_from_stage3a": len(scenarios),
            "actual": len(sec_records),
        })
    if actual_list_nos != expected_list_nos:
        errors.append({
            "stage": "stage3b",
            "error": "list_no_mismatch_with_stage3a",
            "expected_from_stage3a": expected_list_nos,
            "actual": actual_list_nos,
        })
    stage3a_mf_id = stage3a_effective_mf_id(stage3a, None)
    if mf_id and stage3a_mf_id and not text_equal_ignoring_space(mf_id, stage3a_mf_id):
        errors.append({
            "stage": "stage3b",
            "error": "mf_id_mismatch_with_stage3a",
            "expected": stage3a_mf_id,
            "actual": mf_id,
        })


def check_stage3b_sec(
    data: Any,
    min_scenarios: int,
    max_scenarios: int,
    mf_id: str | None,
    errors: list[dict[str, Any]],
    stage3a: Any | None = None,
) -> None:
    """Validate Stage 3B SEC output (sec_records format)."""
    if not isinstance(data, dict):
        errors.append({"stage": "stage3b", "error": "top_level_must_be_object"})
        return
    check_stage3b_top_level(data, errors)
    effective_mf_id = stage3b_effective_mf_id(data, mf_id)

    if not has_compact_key(data, "meta"):
        errors.append({"stage": "stage3b", "error": "meta_missing"})
    else:
        meta = get_by_compact_key(data, "meta")
        if not isinstance(meta, dict):
            errors.append({"stage": "stage3b", "error": "meta_must_be_object"})
        else:
            for field in ["run_id", "mf_id", "stage"]:
                if not has_compact_key(meta, field) or is_blankish(get_by_compact_key(meta, field)):
                    errors.append({
                        "stage": "stage3b",
                        "error": "meta_missing_field",
                        "field": field,
                    })
            if not text_equal_ignoring_space(get_by_compact_key(meta, "stage"), "stage3b"):
                errors.append({
                    "stage": "stage3b",
                    "error": "meta_stage_must_be_stage3b",
                    "actual": get_by_compact_key(meta, "stage"),
                })
            meta_mf_id = str(get_by_compact_key(meta, "mf_id") or get_by_compact_key(meta, "MF_ID") or "").strip()
            if mf_id and meta_mf_id and not text_equal_ignoring_space(mf_id, meta_mf_id):
                errors.append({
                    "stage": "stage3b",
                    "error": "mf_id_mismatch",
                    "expected": mf_id,
                    "actual": meta_mf_id,
                })

    if not has_compact_key(data, "sec_records"):
        errors.append({"stage": "stage3b", "error": "sec_records_missing"})
        return

    sec_records = get_by_compact_key(data, "sec_records")
    if not isinstance(sec_records, list):
        errors.append({"stage": "stage3b", "error": "sec_records_must_be_array"})
        return

    # Check scenario count
    if len(sec_records) < min_scenarios or len(sec_records) > max_scenarios:
        errors.append({
            "stage": "stage3b",
            "error": "sec_records_count_out_of_range",
            "min": min_scenarios,
            "max": max_scenarios,
            "actual": len(sec_records),
        })

    seen_list_nos: set[int] = set()
    for index, record in enumerate(sec_records, start=1):
        if not isinstance(record, dict):
            errors.append({
                "stage": "stage3b",
                "row": index,
                "error": "sec_record_must_be_object",
            })
            continue

        forbidden_fields = sorted(field for field in STAGE3B_FORBIDDEN_RECORD_FIELDS if field in record)
        if forbidden_fields:
            errors.append({
                "stage": "stage3b",
                "row": index,
                "error": "stage3a_fields_must_not_be_repeated_in_stage3b",
                "fields": forbidden_fields,
            })

        list_no = parse_positive_int(get_by_alias(record, "List_No"))
        if list_no is None:
            errors.append({
                "stage": "stage3b",
                "row": index,
                "error": "list_no_must_be_positive_integer",
                "actual": get_by_alias(record, "List_No"),
            })
        else:
            if list_no in seen_list_nos:
                errors.append({
                    "stage": "stage3b",
                    "row": index,
                    "error": "duplicate_list_no",
                    "List_No": list_no,
                })
            seen_list_nos.add(list_no)
            if stage3a is None and list_no != index:
                errors.append({
                    "stage": "stage3b",
                    "row": index,
                    "error": "list_no_must_be_consecutive",
                    "expected": index,
                    "actual": get_by_alias(record, "List_No"),
                })

        missing = [field for field in STAGE3B_REQUIRED_FIELDS if not has_compact_key(record, field)]
        if missing:
            errors.append({
                "stage": "stage3b",
                "row": index,
                "error": "sec_record_missing_required_fields",
                "fields": missing,
            })

        blank_fields = [
            field
            for field in STAGE3B_REQUIRED_FIELDS
            if has_compact_key(record, field)
            and field != "sec_reasoning"
            and is_blankish(get_by_compact_key(record, field))
        ]
        if blank_fields:
            errors.append({
                "stage": "stage3b",
                "row": index,
                "error": "sec_record_required_fields_must_not_be_blank",
                "fields": blank_fields,
            })

        sec_reasoning = get_by_compact_key(record, "sec_reasoning")
        if not sec_reasoning or not isinstance(sec_reasoning, dict):
            errors.append({
                "stage": "stage3b",
                "row": index,
                "error": "sec_reasoning_missing_or_not_object",
            })
            continue

        for rating_type, required_reasoning_fields in STAGE3B_REASONING_REQUIRED_FIELDS.items():
            rating_reasoning = get_by_compact_key(sec_reasoning, rating_type)
            if not isinstance(rating_reasoning, dict):
                errors.append({
                    "stage": "stage3b",
                    "row": index,
                    "error": "sec_reasoning_missing_rating_object",
                    "rating_type": rating_type,
                })
                continue
            missing_reasoning = [
                field
                for field in required_reasoning_fields
                if not has_compact_key(rating_reasoning, field) or is_blankish(get_by_compact_key(rating_reasoning, field))
            ]
            if missing_reasoning:
                errors.append({
                    "stage": "stage3b",
                    "row": index,
                    "error": "sec_reasoning_missing_required_fields",
                    "rating_type": rating_type,
                    "fields": missing_reasoning,
                })

        normalized_levels: dict[str, str] = {}
        for record_field, rating_type, reasoning_field, prefix in STAGE3B_LEVEL_FIELDS:
            record_level = normalize_sec(get_by_compact_key(record, record_field), prefix)
            normalized_levels[prefix] = record_level or ""
            if record_level is None:
                errors.append({
                    "stage": "stage3b",
                    "row": index,
                    "error": "invalid_sec_level",
                    "field": record_field,
                    "actual": get_by_compact_key(record, record_field),
                })
            rating_reasoning = get_by_compact_key(sec_reasoning, rating_type)
            if not isinstance(rating_reasoning, dict):
                continue
            reasoning_level = normalize_sec(get_by_compact_key(rating_reasoning, reasoning_field), prefix)
            if reasoning_level is None:
                errors.append({
                    "stage": "stage3b",
                    "row": index,
                    "error": "invalid_reasoning_sec_level",
                    "rating_type": rating_type,
                    "field": reasoning_field,
                    "actual": get_by_compact_key(rating_reasoning, reasoning_field),
                })
            elif record_level is not None and reasoning_level != record_level:
                errors.append({
                    "stage": "stage3b",
                    "row": index,
                    "error": "sec_level_mismatch_with_reasoning",
                    "field": record_field,
                    "reasoning_field": f"{rating_type}.{reasoning_field}",
                    "expected": record_level,
                    "actual": reasoning_level,
                })

        expected_asil, actual_asil = check_asil_consistency(record, "stage3b", index, errors)
        if all(normalized_levels.values()):
            expected_formula = sec_formula_fragment(
                normalized_levels["S"],
                normalized_levels["E"],
                normalized_levels["C"],
            )
            actual_asil_text = compact_text(get_by_compact_key(record, ASIL_FIELD))
            if expected_formula not in actual_asil_text:
                errors.append({
                    "stage": "stage3b",
                    "row": index,
                    "error": "asil_formula_mismatch_with_sec",
                    "expected_fragment": expected_formula,
                    "actual": get_by_compact_key(record, ASIL_FIELD),
                })

        asil_for_ftti = actual_asil or expected_asil
        ftti_value = get_by_compact_key(record, "FTTI(ms)")
        ftti_reason = get_by_compact_key(record, "FTTI理由")
        if asil_for_ftti and asil_for_ftti != "QM":
            if is_blankish(ftti_value):
                errors.append({
                    "stage": "stage3b",
                    "row": index,
                    "error": "ftti_required_for_non_qm",
                    "ASIL": asil_for_ftti,
                })
            elif not ftti_is_numeric(ftti_value):
                errors.append({
                    "stage": "stage3b",
                    "row": index,
                    "error": "ftti_must_be_numeric_ms",
                    "actual": ftti_value,
                })
            if is_blankish(ftti_reason):
                errors.append({
                    "stage": "stage3b",
                    "row": index,
                    "error": "ftti_reason_required_for_non_qm",
                })
        elif not is_blankish(ftti_value):
            if not ftti_is_numeric(ftti_value):
                errors.append({
                    "stage": "stage3b",
                    "row": index,
                    "error": "ftti_must_be_numeric_ms",
                    "actual": ftti_value,
                })
            if is_blankish(ftti_reason):
                errors.append({
                    "stage": "stage3b",
                    "row": index,
                    "error": "ftti_reason_required_when_ftti_present",
                })

    check_stage3b_against_stage3a(sec_records, stage3a, effective_mf_id, errors)

    for field in ["safety_goal", "safe_state"]:
        value = get_by_compact_key(data, field)
        if is_blankish(value):
            errors.append({"stage": "stage3b", "error": f"{field}_missing_or_blank"})
        elif not isinstance(value, str):
            errors.append({
                "stage": "stage3b",
                "error": f"{field}_must_be_string",
                "actual_type": type(value).__name__,
            })


def check_stage3b_merged_hara(data: Any, min_scenarios: int, max_scenarios: int, mf_id: str | None, errors: list[dict[str, Any]]) -> None:
    """Validate Stage 3B complete HARA JSON."""
    if not isinstance(data, dict):
        errors.append({"stage": "stage3b", "error": "top_level_must_be_object"})
        return

    # Check that max_asil_planning from Stage 3A is preserved
    if not has_compact_key(data, "max_asil_planning"):
        errors.append({"stage": "stage3b", "error": "max_asil_planning_missing_from_stage3a"})

    # Use existing check_stage3 for HARA columns
    check_stage3(data, min_scenarios, max_scenarios, mf_id, errors)

    # Check sec_reasoning exists
    if not has_compact_key(data, "sec_reasoning"):
        errors.append({"stage": "stage3b", "error": "sec_reasoning_missing"})
    else:
        sec_reasoning = get_by_compact_key(data, "sec_reasoning")
        if not isinstance(sec_reasoning, list):
            errors.append({"stage": "stage3b", "error": "sec_reasoning_must_be_array"})
        else:
            # Check each sec_reasoning entry has required fields
            for index, entry in enumerate(sec_reasoning, start=1):
                if not isinstance(entry, dict):
                    continue
                for rating_type in ["S评级推理", "E评级推理", "C评级推理"]:
                    if not has_compact_key(entry, rating_type):
                        errors.append({
                            "stage": "stage3b",
                            "row": index,
                            "error": "sec_reasoning_missing_rating",
                            "rating_type": rating_type,
                        })

    # Check that scenario_reasoning from Stage 3A is preserved
    if not has_compact_key(data, "scenario_reasoning"):
        errors.append({"stage": "stage3b", "error": "scenario_reasoning_missing_from_stage3a"})
    else:
        scenario_reasoning = get_by_compact_key(data, "scenario_reasoning")
        if not isinstance(scenario_reasoning, list):
            errors.append({"stage": "stage3b", "error": "scenario_reasoning_must_be_array"})
        else:
            # Check each scenario_reasoning entry has required fields
            for index, entry in enumerate(scenario_reasoning, start=1):
                if not isinstance(entry, dict):
                    continue
                for field in ["场景规划理由", "危害事件推理", "场景条件相关性检查"]:
                    if not has_compact_key(entry, field):
                        errors.append({
                            "stage": "stage3b",
                            "row": index,
                            "error": "scenario_reasoning_missing_field",
                            "field": field,
                        })

    # Check that all SEC fields are present (not nan)
    hara = rows(data, "hara")
    for index, row in enumerate(hara, start=1):
        for field in [SEC_S_FIELD, SEC_E_FIELD, SEC_C_FIELD, ASIL_FIELD]:
            value = get_by_compact_key(row, field)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                errors.append({
                    "stage": "stage3b",
                    "row": index,
                    "error": "sec_field_missing_or_empty",
                    "field": field,
                })


def normalize_known_rows(
    source_rows: list[dict[str, Any]],
    columns: list[str],
    keep_alias_keys: set[str] | None = None,
) -> list[dict[str, Any]]:
    known_keys = {
        compact_field_name(candidate)
        for column in columns
        for candidate in [column, *ALIASES.get(column, [])]
    }
    keep_alias_compacts = {compact_field_name(key) for key in keep_alias_keys or set()}
    normalized_rows = normalize_rows(source_rows, columns)
    for source_row, normalized_row in zip(source_rows, normalized_rows):
        for key, value in source_row.items():
            compact_key = compact_field_name(key)
            if key not in normalized_row and (compact_key not in known_keys or compact_key in keep_alias_compacts):
                normalized_row[key] = value
    return normalized_rows


def normalize_stage_data(data: Any, stage: str) -> Any:
    if not isinstance(data, dict):
        return data
    normalized = dict(data)
    if stage in {"stage1", "stage1_slice"} and has_compact_key(data, "derive_mf"):
        normalized["derive_mf"] = normalize_known_rows(
            rows(data, "derive_mf"),
            DERIVE_MF_COLUMNS,
            keep_alias_keys=set(STAGE1_MERGED_FAULT_FIELDS),
        )
    elif stage in {"stage2", "stage2_slice"} and has_compact_key(data, "mf_vehicle_hazards"):
        normalized["mf_vehicle_hazards"] = normalize_known_rows(rows(data, "mf_vehicle_hazards"), MF_VEHICLE_HAZARDS_COLUMNS)
    elif stage == "stage3" and has_compact_key(data, "hara"):
        normalized["hara"] = normalize_known_rows(rows(data, "hara"), HARA_COLUMNS)
    elif stage == "stage3a" and has_compact_key(data, "scenarios"):
        normalized["scenarios"] = normalize_known_rows(rows(data, "scenarios"), SCENARIOS_COLUMNS)
    elif stage == "stage3b":
        if has_compact_key(data, "hara"):
            normalized["hara"] = normalize_known_rows(rows(data, "hara"), HARA_COLUMNS)
        if has_compact_key(data, "sec_records"):
            normalized["sec_records"] = normalize_known_rows(rows(data, "sec_records"), SEC_RECORDS_COLUMNS)
    elif stage == "stage4" and has_compact_key(data, "sg_sum"):
        normalized["sg_sum"] = normalize_known_rows(rows(data, "sg_sum"), SG_SUM_COLUMNS)
    return normalized


def safety_goal_key(value: Any) -> str:
    if is_nan_like(value):
        return ""
    return compact_text(value)


def ftti_ms_number(value: Any) -> float | None:
    if is_nan_like(value):
        return None
    match = re.search(r"\d+(?:\.\d+)?", str(value))
    return float(match.group(0)) if match else None


def sg_summary_group_key(mf_id: Any, safety_goal: Any) -> str:
    mf_text = compact_text(mf_id)
    goal_key = safety_goal_key(safety_goal)
    return f"{mf_text}\0{goal_key}" if mf_text and goal_key else ""


def expected_stage4_sg_groups(hara_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for row in hara_rows:
        asil = normalize_asil(row.get("结果ASIL"))
        if asil is None or asil == "QM":
            continue
        mf_id = str(row.get("MF_ID") or "").strip()
        if not mf_id:
            continue
        goal = str(row.get("安全目标") or "").strip()
        key = safety_goal_key(goal)
        if not key:
            continue
        group_key = sg_summary_group_key(mf_id, goal)
        group = groups.setdefault(group_key, {
            "MF_ID": mf_id,
            "安全目标": goal,
            "ASIL Level": asil,
            "FTTI(ms)": row.get("FTTI(ms)"),
            "ftti_number": ftti_ms_number(row.get("FTTI(ms)")),
        })
        if ASIL_ORDER[asil] > ASIL_ORDER[group["ASIL Level"]]:
            group["ASIL Level"] = asil
        row_ftti = ftti_ms_number(row.get("FTTI(ms)"))
        if row_ftti is not None and (group["ftti_number"] is None or row_ftti < group["ftti_number"]):
            group["FTTI(ms)"] = row.get("FTTI(ms)")
            group["ftti_number"] = row_ftti
    return groups


def check_stage4(data: Any, hara_data: Any | None, errors: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> None:
    sg_sum = rows(data, "sg_sum")
    seen_group_keys: set[str] = set()
    for index, row in enumerate(sg_sum, start=1):
        missing = missing_fields(row, SG_SUM_COLUMNS)
        if missing:
            warnings.append({
                "stage": "stage4",
                "row": index,
                "warning": "missing_required_fields_auto_fixable",
                "fields": missing,
                "message": "最终 validate_hara_json.py 会基于 HARA 的 MF_ID + 安全目标分组重建或修正 SG_Sum。",
            })
        group_key = sg_summary_group_key(row.get("MF_ID"), row.get("安全目标"))
        if group_key:
            if group_key in seen_group_keys:
                errors.append({
                    "stage": "stage4",
                    "row": index,
                    "error": "duplicate_mf_safety_goal_summary",
                    "MF_ID": row.get("MF_ID"),
                    "安全目标": row.get("安全目标"),
                    "message": "SG_Sum 应按同一 MF_ID 内相同安全目标汇总；同一 MF_ID + 安全目标只能保留一条。",
                })
            seen_group_keys.add(group_key)
        operation_mode = str(row.get("操作模式") or "").strip()
        if is_nan_like(operation_mode) or text_in_ignoring_space(operation_mode, OPERATION_MODE_PLACEHOLDERS):
            errors.append({
                "stage": "stage4",
                "row": index,
                "error": "operation_mode_missing_or_placeholder",
                "MF_ID": row.get("MF_ID"),
                "安全目标": row.get("安全目标"),
                "message": "Stage4 只允许大模型填写操作模式；运行 check 前必须把占位值替换为具体操作模式。",
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
                "warning": "qm_safety_goal_will_be_removed_from_sg_sum",
                "MF_ID": row.get("MF_ID"),
                "安全目标": row.get("安全目标"),
            })

    if hara_data is None:
        return
    expected_groups = expected_stage4_sg_groups(rows_any(hara_data, "hara", "HARA"))
    actual_group_keys = {
        sg_summary_group_key(row.get("MF_ID"), row.get("安全目标"))
        for row in sg_sum
        if sg_summary_group_key(row.get("MF_ID"), row.get("安全目标"))
    }
    for index, row in enumerate(sg_sum, start=1):
        group_key = sg_summary_group_key(row.get("MF_ID"), row.get("安全目标"))
        if not group_key:
            warnings.append({
                "stage": "stage4",
                "row": index,
                "warning": "sg_mf_id_or_safety_goal_missing_auto_fixable",
                "message": "SG_Sum 行缺少 MF_ID 或安全目标，最终会按 HARA 的 MF_ID + 安全目标重建。",
            })
            continue
        expected = expected_groups.get(group_key)
        if expected is None:
            continue
        actual_asil = normalize_asil(row.get("ASIL Level"))
        expected_asil = expected["ASIL Level"]
        if actual_asil != expected_asil:
            errors.append({
                "stage": "stage4",
                "row": index,
                "error": "sg_asil_mismatch_with_mf_safety_goal_highest",
                "MF_ID": row.get("MF_ID"),
                "安全目标": row.get("安全目标"),
                "actual": row.get("ASIL Level"),
                "expected_highest_from_hara": expected_asil,
            })
        expected_ftti = expected.get("ftti_number")
        if expected_ftti is not None:
            actual_ftti = ftti_ms_number(row.get("FTTI(ms)"))
            if actual_ftti is None or abs(actual_ftti - expected_ftti) > 1e-9:
                errors.append({
                    "stage": "stage4",
                    "row": index,
                    "error": "sg_ftti_not_min_for_mf_safety_goal",
                    "MF_ID": row.get("MF_ID"),
                    "安全目标": row.get("安全目标"),
                    "actual": row.get("FTTI(ms)"),
                    "expected_min_from_hara": expected.get("FTTI(ms)"),
                })
        if not text_equal_ignoring_space(row.get("MF_ID"), expected["MF_ID"]):
            warnings.append({
                "stage": "stage4",
                "row": index,
                "warning": "sg_mf_id_mismatch_auto_fixable",
                "安全目标": row.get("安全目标"),
                "actual": row.get("MF_ID"),
                "expected": expected["MF_ID"],
            })
    missing = sorted(set(expected_groups) - actual_group_keys)
    unknown = sorted(actual_group_keys - set(expected_groups))
    if missing:
        warnings.append({
            "stage": "stage4",
            "warning": "non_qm_mf_safety_goal_missing_sg_sum_entry_auto_fixable",
            "mf_safety_goal_keys": missing,
        })
    if unknown:
        warnings.append({
            "stage": "stage4",
            "warning": "sg_sum_references_unknown_mf_safety_goal_will_be_removed",
            "mf_safety_goal_keys": unknown,
        })


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["stage0", "stage1", "stage1_slice", "stage2", "stage2_slice", "stage3", "stage3a", "stage3b", "stage3b_raw", "stage4"], required=True)
    parser.add_argument("--json", required=True)
    parser.add_argument("--stage0")
    parser.add_argument("--stage1")
    parser.add_argument("--stage2")
    parser.add_argument("--stage3a")
    parser.add_argument("--hara")
    parser.add_argument("--operation-scenarios")
    parser.add_argument("--function-id")
    parser.add_argument("--mf-id")
    parser.add_argument("--min-scenarios", type=int, default=10)
    parser.add_argument("--max-scenarios", type=int, default=20)
    parser.add_argument("--fix", action="store_true", help="Normalize known stage row keys to canonical schema when validation passes.")
    args = parser.parse_args()

    json_path = Path(args.json)
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    effective_stage = "stage3b" if args.stage == "stage3b_raw" else args.stage
    data = normalize_stage_data(normalize_whitespace(load_json(json_path)), effective_stage)

    if args.stage == "stage0":
        check_stage0(data, errors)
    elif args.stage == "stage1":
        stage0 = normalize_whitespace(load_json(Path(args.stage0))) if args.stage0 else None
        check_stage1(data, stage0, errors, warnings, auto_fix=args.fix)
    elif args.stage == "stage1_slice":
        stage0 = normalize_whitespace(load_json(Path(args.stage0))) if args.stage0 else None
        check_stage1_slice(data, stage0, args.function_id, errors, warnings, auto_fix=args.fix)
    elif args.stage == "stage2":
        stage1 = normalize_stage_data(normalize_whitespace(load_json(Path(args.stage1))), "stage1") if args.stage1 else None
        check_stage2(data, stage1, errors, warnings)
    elif args.stage == "stage2_slice":
        stage1 = normalize_stage_data(normalize_whitespace(load_json(Path(args.stage1))), "stage1_slice") if args.stage1 else None
        check_stage2_slice(data, stage1, args.function_id, errors, warnings)
    elif args.stage == "stage3":
        check_stage3(data, args.min_scenarios, args.max_scenarios, args.mf_id, errors)
        stage2 = normalize_stage_data(normalize_whitespace(load_json(Path(args.stage2))), "stage2") if args.stage2 else None
        check_stage3_against_stage2(data, stage2, errors)
        operation_scenarios = normalize_whitespace(load_json(Path(args.operation_scenarios))) if args.operation_scenarios else None
        check_stage3_operation_scenarios(data, operation_scenarios, errors)
    elif args.stage == "stage3a":
        stage2 = normalize_stage_data(normalize_whitespace(load_json(Path(args.stage2))), "stage2") if args.stage2 else None
        operation_scenarios = normalize_whitespace(load_json(Path(args.operation_scenarios))) if args.operation_scenarios else None
        # 自动修正格式问题（空格、括号等）
        if args.fix:
            format_fixes = apply_scenario_enum_format_fixes(data, operation_scenarios)
            if format_fixes:
                warnings.append({
                    "stage": "stage3a_format_fix",
                    "message": f"已自动修正 {len(format_fixes)} 个格式问题（空格、括号等）",
                    "fixes": format_fixes,
                })
        # 自动应用"不涉及"修改
        if args.fix:
            fixes = apply_scenario_condition_corrections(data)
            if fixes:
                warnings.append({
                    "stage": "stage3a_auto_fix",
                    "message": f"已根据 scenario_reasoning 自动将 {len(fixes)} 个字段修改为 '不涉及'",
                    "fixes": fixes,
                })
        check_stage3a(data, args.min_scenarios, args.max_scenarios, args.mf_id, errors, stage2)
        check_stage3a_condition_consistency(rows(data, "scenarios"), errors)
        check_stage3a_operation_scenarios(data, operation_scenarios, errors)
    elif args.stage in {"stage3b", "stage3b_raw"}:
        if args.stage == "stage3b_raw":
            warnings.append({
                "stage": "stage3b",
                "warning": "deprecated_stage_name",
                "message": "stage3b_raw 已改名为 stage3b；请更新命令为 --stage stage3b。",
            })
        stage3a = normalize_stage_data(normalize_whitespace(load_json(Path(args.stage3a))), "stage3a") if args.stage3a else None
        check_stage3b_sec(data, args.min_scenarios, args.max_scenarios, args.mf_id, errors, stage3a)
    elif args.stage == "stage4":
        hara_data = normalize_stage_data(normalize_whitespace(load_json(Path(args.hara))), "stage3") if args.hara else None
        check_stage4(data, hara_data, errors, warnings)

    fixed = False
    fixable_stages = {"stage1", "stage1_slice", "stage2", "stage2_slice", "stage3", "stage3a", "stage3b", "stage4"}
    if args.fix and not errors and effective_stage in fixable_stages:
        dump_json(normalize_stage_data(data, effective_stage), json_path)
        fixed = True

    summary = {
        "ok": not errors,
        "stage": effective_stage,
        "file": args.json,
        "fixed": fixed,
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
