#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge Stage 3A scenarios and Stage 3B SEC ratings into complete HARA JSON."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    """Load JSON file with UTF-8 encoding."""
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Error parsing {path}: {exc.msg}")
    except FileNotFoundError:
        raise SystemExit(f"File not found: {path}")


def merge_hara(stage3a_data: dict, stage3b_data: dict) -> dict:
    """Merge Stage 3A scenarios and Stage 3B SEC ratings.

    Args:
        stage3a_data: Stage 3A JSON with scenarios
        stage3b_data: Stage 3B JSON with sec_records

    Returns:
        Complete HARA JSON with merged records
    """
    # Get scenarios from stage3a
    scenarios = stage3a_data.get("scenarios", [])
    if not scenarios:
        raise SystemExit("No scenarios found in Stage 3A data")

    # Get SEC records from stage3b
    sec_records = stage3b_data.get("sec_records", [])
    if not sec_records:
        raise SystemExit("No SEC records found in Stage 3B data")

    # Build lookup by List_No
    sec_by_no = {record["List_No"]: record for record in sec_records}

    # Merge each scenario with its SEC record
    hara_records = []
    for scenario in scenarios:
        list_no = scenario.get("List_No")
        if list_no is None:
            continue

        sec_record = sec_by_no.get(list_no)
        if sec_record is None:
            print(f"Warning: No SEC record for List_No={list_no}", file=sys.stderr)
            continue

        # Merge scenario and SEC record
        # Extract scenario_reasoning from scenario (remove from scenario to avoid duplication in merged record)
        scenario_reasoning = scenario.get("scenario_reasoning")
        # Extract sec_reasoning from sec_record (remove from sec_record to avoid duplication in merged record)
        sec_reasoning = sec_record.get("sec_reasoning")

        merged = {
            "List_No": list_no,
            "MF_ID": scenario.get("MF_ID"),
            "故障描述": scenario.get("故障描述"),
            "整车危害": scenario.get("整车危害"),
            "道路类型": scenario.get("道路类型"),
            "道路条件": scenario.get("道路条件"),
            "环境条件": scenario.get("环境条件"),
            "车辆状态": scenario.get("车辆状态"),
            "车速(km/h)": scenario.get("车速(km/h)"),
            "特殊要素": scenario.get("特殊要素"),
            "附加条件": scenario.get("附加条件"),
            "驾驶员是否在车上": scenario.get("驾驶员是否在车上"),
            "危害事件": scenario.get("危害事件"),
            "E-解释": sec_record.get("E-解释"),
            "暴露频率'E'": sec_record.get("暴露频率'E'"),
            "有风险的人员": sec_record.get("有风险的人员"),
            "可能的后果('S'的理由)": sec_record.get("可能的后果('S'的理由)"),
            "Severity 'S'": sec_record.get("Severity 'S'"),
            "C-解释": sec_record.get("C-解释"),
            "控制能力 'C'": sec_record.get("控制能力 'C'"),
            "结果ASIL": sec_record.get("结果ASIL"),
            "FTTI(ms)": sec_record.get("FTTI(ms)"),
            "备注": sec_record.get("备注", ""),
        }
        # Add reasoning if present (参照 stage3a/scenario_reasoning 写法，在每条记录内部)
        if scenario_reasoning:
            merged["scenario_reasoning"] = scenario_reasoning
        if sec_reasoning:
            merged["sec_reasoning"] = sec_reasoning
        hara_records.append(merged)

    # Build merged output
    meta = stage3a_data.get("meta", {})
    meta["stage"] = "stage3"

    return {
        "meta": meta,
        "max_asil_planning": stage3a_data.get("max_asil_planning"),
        "hara": hara_records,
        "safety_goal": stage3b_data.get("safety_goal"),
        "safe_state": stage3b_data.get("safe_state"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge Stage 3A scenarios and Stage 3B SEC ratings into complete HARA JSON"
    )
    parser.add_argument("--stage3a", required=True, help="Path to Stage 3A JSON file")
    parser.add_argument("--stage3b", required=True, help="Path to Stage 3B JSON file")
    parser.add_argument("--output", required=True, help="Output path for merged HARA JSON")
    parser.add_argument("--compact", action="store_true", help="Output compact JSON (default: pretty formatted)")
    args = parser.parse_args()

    # Load input files
    stage3a_data = load_json(Path(args.stage3a))
    stage3b_data = load_json(Path(args.stage3b))

    # Merge
    merged_data = merge_hara(stage3a_data, stage3b_data)

    # Write output (默认美化格式，便于查看)
    output_path = Path(args.output)
    indent = None if args.compact else 2
    output_path.write_text(
        json.dumps(merged_data, ensure_ascii=False, indent=indent),
        encoding="utf-8",
    )

    # Print summary
    num_hara = len(merged_data.get("hara", []))
    print(f"Merged {num_hara} HARA records to {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
