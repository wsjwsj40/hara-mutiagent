#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legacy helper to apply the project ASIL rule to HARA JSON.

The standard multi-agent flow now relies on check_stage_json.py to catch ASIL
mismatches before Stage 4. Keep this script only for manual recovery or old
artifacts that need deterministic ASIL normalization.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from hara_schema_columns import normalize_row, HARA_COLUMNS, is_nan_like
    from asil_matrix import asil_from_sec, normalize_asil
except ImportError:  # pragma: no cover
    from .hara_schema_columns import normalize_row, HARA_COLUMNS, is_nan_like
    from .asil_matrix import asil_from_sec, normalize_asil

HARA_KEYS = ["hara", "HARA", "hara_rows", "HARA_rows", "scenarios", "scenario_rows", "analysis_rows", "result_rows"]


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


def find_hara_container(data: Any) -> tuple[list[dict[str, Any]], str | None]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)], None
    if isinstance(data, dict):
        for key in HARA_KEYS:
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)], key
        # Some outputs are {rows: [...]}.
        for key in ("rows", "data", "result", "items"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)], key
    return [], None


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


def apply_matrix_to_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    warnings: list[dict[str, Any]] = []
    fixed_rows: list[dict[str, Any]] = []
    for idx, raw in enumerate(rows, start=1):
        row = normalize_row(raw, HARA_COLUMNS)
        calculated = asil_from_sec(row.get("Severity 'S'"), row.get("暴露频率'E'"), row.get("控制能力 'C'"))
        original = normalize_asil(row.get("结果ASIL"))
        if calculated is None:
            warnings.append({
                "level": "WARNING",
                "stage": "apply_asil_matrix",
                "row": idx,
                "List_No": row.get("List_No"),
                "MF_ID": row.get("MF_ID"),
                "message": "无法从 S/E/C 解析 ASIL，保留原结果ASIL。",
                "severity": row.get("Severity 'S'"),
                "exposure": row.get("暴露频率'E'"),
                "controllability": row.get("控制能力 'C'"),
                "original_asil": row.get("结果ASIL"),
            })
        elif original != calculated:
            warnings.append({
                "level": "WARNING",
                "stage": "apply_asil_matrix",
                "row": idx,
                "List_No": row.get("List_No"),
                "MF_ID": row.get("MF_ID"),
                "message": "结果ASIL 与 S/E/C 后缀求和规则不一致，已自动修正。",
                "severity": row.get("Severity 'S'"),
                "exposure": row.get("暴露频率'E'"),
                "controllability": row.get("控制能力 'C'"),
                "original_asil": row.get("结果ASIL"),
                "calculated_asil": calculated,
            })
        if calculated is not None:
            row["结果ASIL"] = calculated
            safety_changes = sync_safety_fields(row, calculated)
            if safety_changes:
                warnings.append({
                    "level": "WARNING",
                    "stage": "safety_field_sync",
                    "row": idx,
                    "List_No": row.get("List_No"),
                    "MF_ID": row.get("MF_ID"),
                    "message": "已根据 ASIL 校验结果同步安全目标、安全状态或 FTTI。",
                    "calculated_asil": calculated,
                    "changes": safety_changes,
                })
        fixed_rows.append(row)
    return fixed_rows, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "--json", dest="input_path", required=True)
    parser.add_argument("--output", "--out", dest="output_path", required=True)
    args = parser.parse_args()

    input_path = Path(args.input_path)
    output_path = Path(args.output_path)
    data = load_json(input_path)
    rows, key = find_hara_container(data)
    fixed_rows, warnings = apply_matrix_to_rows(rows)

    if isinstance(data, list):
        output_data: Any = fixed_rows
    elif isinstance(data, dict):
        output_data = dict(data)
        output_key = key or "hara"
        output_data[output_key] = fixed_rows
        review_log = output_data.get("review_log")
        if not isinstance(review_log, list):
            review_log = []
        review_log.append({
            "stage": "stage3_asil_rule_check",
            "target": input_path.name,
            "result": "pass",
            "warnings": warnings,
            "notes": "已使用 Python ASIL 工具根据 Severity 'S'、暴露频率'E'、控制能力 'C' 的后缀求和规则自动校验并修正结果ASIL。",
        })
        output_data["review_log"] = review_log
    else:
        raise SystemExit("Input JSON must be an object or a list")

    dump_json(output_data, output_path)
    print(json.dumps({
        "ok": True,
        "input": str(input_path),
        "output": str(output_path),
        "hara_rows": len(fixed_rows),
        "warnings": len(warnings),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
