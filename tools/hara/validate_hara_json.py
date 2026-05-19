#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate and normalize staged/merged HARA JSON.

basic mode: only normalize fields and keep Excel export unblocked.
strict mode: add optional quality checks such as scenario count.

This script intentionally accepts --min-scenarios/--max-scenarios even in basic
mode so it stays compatible with run_hara_export.py.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    from hara_schema_columns import SHEET_COLUMNS, normalize_rows, is_nan_like
    from asil_matrix import ASIL_ORDER, asil_from_sec, normalize_asil
except ImportError:  # pragma: no cover
    from .hara_schema_columns import SHEET_COLUMNS, normalize_rows, is_nan_like
    from .asil_matrix import ASIL_ORDER, asil_from_sec, normalize_asil

SHEET_ALIASES = {
    "DeriveMF": ["DeriveMF", "derive_mf", "deriveMF", "stage1_derive_mf"],
    "MF and Vehicle Hazards": [
        "MF and Vehicle Hazards", "mf_vehicle_hazards", "vehicle_hazards", "stage2_mf_vehicle_hazards"
    ],
    "HARA": ["HARA", "hara", "hara_rows", "HARA_rows", "scenarios", "scenario_rows"],
    "SG_Sum": ["SG_Sum", "sg_sum", "safety_goals", "safety_goal_summary"],
}


def load_json(path: Path) -> Any:
    text = path.read_text(encoding="utf-8-sig").strip()
    if text.startswith("```json"):
        text = text[len("```json"):].strip()
    if text.startswith("```"):
        text = text[3:].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return json.loads(text)


def dump_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def as_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        # Some model outputs wrap rows in {rows: [...]} or {data: [...]}.
        for key in ("rows", "data", "result", "items"):
            if isinstance(value.get(key), list):
                return [item for item in value[key] if isinstance(item, dict)]
    return []


def find_sheet_rows(data: dict[str, Any], sheet_name: str) -> list[dict[str, Any]]:
    for key in SHEET_ALIASES[sheet_name]:
        if key in data:
            return as_rows(data[key])
    return []


def strict_scenario_count_warnings(normalized: dict[str, Any], min_scenarios: int, max_scenarios: int) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    rows_by_mf: dict[str, int] = defaultdict(int)
    for row in normalized.get("HARA", []) or []:
        mf_id = str(row.get("MF_ID", "nan")).strip()
        if mf_id and mf_id.lower() != "nan":
            rows_by_mf[mf_id] += 1
    for mf_id, count in sorted(rows_by_mf.items()):
        if count < min_scenarios:
            warnings.append({
                "level": "ERROR",
                "stage": "strict",
                "sheet": "HARA",
                "message": f"{mf_id} 的 HARA 场景数量不足：{count} 条，要求至少 {min_scenarios} 条",
            })
        elif count > max_scenarios:
            warnings.append({
                "level": "ERROR",
                "stage": "strict",
                "sheet": "HARA",
                "message": f"{mf_id} 的 HARA 场景数量过多：{count} 条，要求最多 {max_scenarios} 条",
            })
    return warnings


def renumber_hara_rows(normalized: dict[str, Any]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    changed = False
    for index, row in enumerate(normalized.get("HARA", []) or [], start=1):
        expected = str(index)
        if str(row.get("List_No", "")).strip() != expected:
            changed = True
        row["List_No"] = expected
    if changed:
        warnings.append({
            "level": "WARNING",
            "stage": "basic",
            "sheet": "HARA",
            "message": "已将 HARA List_No 重排为从 1 开始的全局连续序号。",
        })
    return warnings


def default_safety_goal(row: dict[str, Any]) -> str:
    hazard = str(row.get("整车危害") or "").strip()
    if is_nan_like(hazard):
        hazard = "相关车辆级危害"
    return f"防止{hazard}导致不可接受的人身伤害风险。"


def default_safe_state(row: dict[str, Any]) -> str:
    hazard = str(row.get("整车危害") or "").strip()
    if "纵向移动" in hazard:
        return "保持车辆静止或使车辆处于驾驶员可控制的驻车保持状态。"
    if "减速" in hazard or "制动" in hazard:
        return "抑制非预期制动输出，使车辆维持驾驶员可控制的纵向运动状态。"
    if "加速" in hazard:
        return "限制非预期驱动力输出，使车辆维持驾驶员可控制的纵向运动状态。"
    if "横摆" in hazard or "侧倾" in hazard or "横向" in hazard:
        return "抑制异常侧向或横摆控制输出，使车辆保持稳定且可控。"
    if "报警" in hazard or "信息" in hazard:
        return "提供正确告警或进入驾驶员可识别、可控制的降级状态。"
    return "进入能够抑制危险行为继续发展的可控安全状态。"


def sync_safety_fields(row: dict[str, Any], asil: str) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    if asil == "QM":
        for field in ("安全目标", "安全状态", "FTTI(ms)"):
            if not is_nan_like(row.get(field)):
                changes.append({"field": field, "action": "cleared_for_qm", "old_value": row.get(field)})
            row[field] = "nan"
        return changes

    if is_nan_like(row.get("安全目标")):
        row["安全目标"] = default_safety_goal(row)
        changes.append({"field": "安全目标", "action": "filled_for_non_qm", "new_value": row["安全目标"]})
    if is_nan_like(row.get("安全状态")):
        row["安全状态"] = default_safe_state(row)
        changes.append({"field": "安全状态", "action": "filled_for_non_qm", "new_value": row["安全状态"]})
    return changes



def correct_hara_asil(normalized: dict[str, Any]) -> list[dict[str, Any]]:
    """Calculate HARA.结果ASIL from S/E/C and overwrite inconsistent LLM output.

    This runs in basic mode as well. It should not block Excel export; it only
    writes warnings when fields are not parseable or when a correction was made.
    """
    warnings: list[dict[str, Any]] = []
    for index, row in enumerate(normalized.get("HARA", []) or [], start=1):
        calculated = asil_from_sec(
            row.get("Severity 'S'"),
            row.get("暴露频率'E'"),
            row.get("控制能力 'C'"),
        )
        original = normalize_asil(row.get("结果ASIL"))
        if calculated is None:
            warnings.append({
                "level": "WARNING",
                "stage": "basic",
                "sheet": "HARA",
                "row": index,
                "message": "无法从 Severity 'S' / 暴露频率'E' / 控制能力 'C' 解析并计算 ASIL，已保留原结果ASIL。",
                "severity": row.get("Severity 'S'"),
                "exposure": row.get("暴露频率'E'"),
                "controllability": row.get("控制能力 'C'"),
                "original_asil": row.get("结果ASIL"),
            })
            continue
        if original != calculated:
            warnings.append({
                "level": "WARNING",
                "stage": "basic",
                "sheet": "HARA",
                "row": index,
                "message": "结果ASIL 与 S/E/C 后缀求和规则不一致，已自动修正。",
                "severity": row.get("Severity 'S'"),
                "exposure": row.get("暴露频率'E'"),
                "controllability": row.get("控制能力 'C'"),
                "original_asil": row.get("结果ASIL"),
                "calculated_asil": calculated,
            })
        row["结果ASIL"] = calculated
        safety_changes = sync_safety_fields(row, calculated)
        if safety_changes:
            warnings.append({
                "level": "WARNING",
                "stage": "safety_field_sync",
                "sheet": "HARA",
                "row": index,
                "message": "已根据 ASIL 校验结果同步安全目标、安全状态或 FTTI。",
                "calculated_asil": calculated,
                "changes": safety_changes,
            })
    return warnings


OPERATION_MODE_PLACEHOLDER = "待Stage4模型填写"


def is_operation_mode_placeholder(value: Any) -> bool:
    text = str(value or "").strip()
    return is_nan_like(text) or text in {
        OPERATION_MODE_PLACEHOLDER,
        "待填写",
        "待补充",
        "待生成",
        "TODO",
        "todo",
    }


def operation_mode_from_hara(row: dict[str, Any]) -> str:
    """Return the Stage 4 placeholder.

    操作模式需要结合功能意图和最高风险场景做语义归纳；不要在确定性
    HARA/SG_Sum 重建里用场景字段机械拼接覆盖模型填写结果。
    """
    return OPERATION_MODE_PLACEHOLDER


def hara_row_quality(row: dict[str, Any]) -> int:
    score = 0
    for field in ("安全目标", "安全状态", "FTTI(ms)", "危害事件"):
        if not is_nan_like(row.get(field)):
            score += 1
    return score


def safety_goal_from_hara(row: dict[str, Any]) -> str:
    value = row.get("安全目标")
    return str(value).strip() if not is_nan_like(value) else default_safety_goal(row)


def normalize_safety_goal_key(value: Any) -> str:
    if is_nan_like(value):
        return ""
    return re.sub(r"\s+", "", str(value).strip())


def parse_ftti_ms(value: Any) -> float | None:
    if is_nan_like(value):
        return None
    match = re.search(r"\d+(?:\.\d+)?", str(value))
    return float(match.group(0)) if match else None


def min_ftti_value(rows: list[dict[str, Any]]) -> str:
    best_value: Any = None
    best_number: float | None = None
    for row in rows:
        value = row.get("FTTI(ms)")
        number = parse_ftti_ms(value)
        if number is None:
            continue
        if best_number is None or number < best_number:
            best_number = number
            best_value = value
    if best_number is None:
        for row in rows:
            value = row.get("FTTI(ms)")
            if not is_nan_like(value):
                return str(value).strip()
        return "nan"
    return str(best_value).strip()


def first_mf_id(rows: list[dict[str, Any]]) -> str:
    mf_ids = sorted({str(row.get("MF_ID") or "").strip() for row in rows if str(row.get("MF_ID") or "").strip()})
    return mf_ids[0] if mf_ids else ""


def sg_group_key(mf_id: str, safety_goal: Any) -> str:
    return f"{mf_id}\0{normalize_safety_goal_key(safety_goal)}"


def representative_hara_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def ftti_rank(row: dict[str, Any]) -> float:
        value = parse_ftti_ms(row.get("FTTI(ms)"))
        return value if value is not None else 10**12

    return max(
        rows,
        key=lambda row: (
            ASIL_ORDER.get(normalize_asil(row.get("结果ASIL")) or "QM", 0),
            hara_row_quality(row),
            -ftti_rank(row),
        ),
    )


def sg_from_hara_group(safety_goal: str, hara_rows: list[dict[str, Any]], sg_no: str) -> dict[str, Any]:
    representative = representative_hara_row(hara_rows)
    highest_asil = max((normalize_asil(row.get("结果ASIL")) or "QM" for row in hara_rows), key=lambda asil: ASIL_ORDER[asil])
    mf_id = first_mf_id(hara_rows)
    min_ftti = min_ftti_value(hara_rows)
    return {
        "SG_No": sg_no,
        "MF_ID": mf_id,
        "安全目标": safety_goal,
        "ASIL Level": highest_asil,
        "安全状态": representative.get("安全状态") if not is_nan_like(representative.get("安全状态")) else default_safe_state(representative),
        "操作模式": operation_mode_from_hara(representative),
        "FTTI(ms)": min_ftti,
        "Comments": (
            f"自动基于 MF_ID={mf_id} 中相同安全目标汇总；"
            f"ASIL Level 取最高={highest_asil}；FTTI(ms) 取最小={min_ftti}；"
            f"代表场景 List_No={representative.get('List_No', 'nan')}；"
            f"操作模式参考：车辆状态={representative.get('车辆状态', 'nan')}，"
            f"道路类型={representative.get('道路类型', 'nan')}，"
            f"道路条件={representative.get('道路条件', 'nan')}，"
            f"驾驶员是否在车上={representative.get('驾驶员是否在车上', 'nan')}，"
            f"危害事件={representative.get('危害事件', 'nan')}。"
        ),
    }


def correct_sg_sum(normalized: dict[str, Any]) -> list[dict[str, Any]]:
    """Rebuild SG_Sum from corrected HARA rows.

    QM rows are removed. Non-QM rows are grouped by MF_ID and identical safety
    goal: ASIL Level takes the highest ASIL in that MF/goal group and FTTI(ms)
    takes the smallest numeric FTTI in that MF/goal group.
    """
    warnings: list[dict[str, Any]] = []
    hara_rows = normalized.get("HARA", []) or []
    groups_by_mf_goal: dict[str, dict[str, Any]] = {}
    for row in hara_rows:
        asil = normalize_asil(row.get("结果ASIL"))
        if asil is None or asil == "QM":
            continue
        mf_id = str(row.get("MF_ID") or "").strip()
        if not mf_id:
            continue
        safety_goal = safety_goal_from_hara(row)
        goal_key = normalize_safety_goal_key(safety_goal)
        if not goal_key:
            continue
        key = sg_group_key(mf_id, safety_goal)
        group = groups_by_mf_goal.setdefault(key, {"MF_ID": mf_id, "安全目标": safety_goal, "rows": []})
        group["rows"].append(row)

    if not groups_by_mf_goal:
        warnings.append({
            "level": "WARNING",
            "stage": "sg_sum_auto_fix",
            "sheet": "SG_Sum",
            "message": "未找到可用于生成 SG_Sum 的 HARA 行，已保留原 SG_Sum 规范化结果。",
        })
        return warnings

    existing_group_keys: set[str] = set()
    existing_by_group: dict[str, dict[str, Any]] = {}
    seen_existing: set[str] = set()
    for index, row in enumerate(normalized.get("SG_Sum", []) or [], start=1):
        mf_id = str(row.get("MF_ID") or "").strip()
        safety_goal = str(row.get("安全目标") or "").strip()
        group_key = sg_group_key(mf_id, safety_goal) if mf_id else ""
        if not group_key or not normalize_safety_goal_key(safety_goal):
            warnings.append({
                "level": "WARNING",
                "stage": "sg_sum_auto_fix",
                "sheet": "SG_Sum",
                "row": index,
                "message": "SG_Sum 行缺少 MF_ID 或安全目标，已丢弃并按 HARA 的 MF_ID + 安全目标自动重建。",
            })
            continue
        if group_key in seen_existing:
            warnings.append({
                "level": "WARNING",
                "stage": "sg_sum_auto_fix",
                "sheet": "SG_Sum",
                "row": index,
                "MF_ID": mf_id,
                "安全目标": safety_goal,
                "message": "同一 MF_ID 内同一安全目标存在重复 SG_Sum 条目，最终 SG_Sum 已按 MF_ID + 安全目标汇总并去重。",
            })
            continue
        seen_existing.add(group_key)
        if group_key not in groups_by_mf_goal:
            warnings.append({
                "level": "WARNING",
                "stage": "sg_sum_auto_fix",
                "sheet": "SG_Sum",
                "row": index,
                "MF_ID": mf_id,
                "安全目标": safety_goal,
                "message": "SG_Sum 引用了 HARA 非 QM 行中不存在的 MF_ID + 安全目标组合，已丢弃。",
            })
            continue
        existing_group_keys.add(group_key)
        existing_by_group[group_key] = row

    corrected: list[dict[str, Any]] = []
    sorted_groups = sorted(
        groups_by_mf_goal.items(),
        key=lambda item: (
            item[1]["MF_ID"],
            item[0],
        ),
    )
    for group_key, group in sorted_groups:
        row = sg_from_hara_group(group["安全目标"], group["rows"], "pending")
        existing = existing_by_group.get(group_key)
        if existing and not is_operation_mode_placeholder(existing.get("操作模式")):
            row["操作模式"] = existing.get("操作模式")
        if group_key not in existing_group_keys:
            warnings.append({
                "level": "WARNING",
                "stage": "sg_sum_auto_fix",
                "sheet": "SG_Sum",
                "MF_ID": group["MF_ID"],
                "安全目标": group["安全目标"],
                "message": "非 QM HARA 的 MF_ID + 安全目标缺少 SG_Sum 条目，已自动补齐。",
            })
        else:
            warnings.append({
                "level": "WARNING",
                "stage": "sg_sum_auto_fix",
                "sheet": "SG_Sum",
                "MF_ID": group["MF_ID"],
                "安全目标": group["安全目标"],
                "message": "SG_Sum 条目已按同一 MF_ID 内相同安全目标自动汇总；ASIL Level 取最高，FTTI(ms) 取最小。",
            })
        corrected.append(row)

    for index, row in enumerate(corrected, start=1):
        row["SG_No"] = f"SG{index:03d}"
    normalized["SG_Sum"] = corrected
    return warnings


def basic_normalize(data: dict[str, Any]) -> dict[str, Any]:
    warnings: list[dict[str, Any]] = []
    normalized: dict[str, Any] = {}

    for sheet_name, columns in SHEET_COLUMNS.items():
        rows = find_sheet_rows(data, sheet_name)
        if not rows:
            warnings.append({
                "level": "WARNING",
                "stage": "basic",
                "sheet": sheet_name,
                "message": f"未找到 {sheet_name} 数据，已生成空 sheet。",
            })
        normalized[sheet_name] = normalize_rows(rows, columns)

    normalized["meta"] = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}
    normalized["function_mapping"] = data.get("function_mapping", [])
    normalized["review_log"] = data.get("review_log", [])
    existing = data.get("Validation_Warnings") or data.get("validation_warnings") or []
    warnings.extend(renumber_hara_rows(normalized))
    warnings.extend(correct_hara_asil(normalized))
    warnings.extend(correct_sg_sum(normalized))
    normalized["Validation_Warnings"] = warnings + (existing if isinstance(existing, list) else [])
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", "--input", dest="json_path", required=True)
    parser.add_argument("--out", "--output", dest="out_path", required=True)
    parser.add_argument("--mode", choices=["basic", "strict"], default="basic")
    # Keep these arguments for compatibility with run_hara_export.py.
    parser.add_argument("--min-scenarios", type=int, default=10)
    parser.add_argument("--max-scenarios", type=int, default=20)
    args = parser.parse_args()

    data = load_json(Path(args.json_path))
    if not isinstance(data, dict):
        raise SystemExit("Top-level JSON must be an object")

    normalized = basic_normalize(data)
    if args.mode == "strict":
        normalized["Validation_Warnings"].extend(
            strict_scenario_count_warnings(normalized, args.min_scenarios, args.max_scenarios)
        )

    dump_json(normalized, Path(args.out_path))
    errors = [w for w in normalized["Validation_Warnings"] if isinstance(w, dict) and w.get("level") == "ERROR"]
    summary = {
        "ok": not errors,
        "mode": args.mode,
        "output": args.out_path,
        "DeriveMF": len(normalized["DeriveMF"]),
        "MF and Vehicle Hazards": len(normalized["MF and Vehicle Hazards"]),
        "HARA": len(normalized["HARA"]),
        "SG_Sum": len(normalized["SG_Sum"]),
        "warnings": len(normalized["Validation_Warnings"]),
        "errors": len(errors),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.mode == "strict" and errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
