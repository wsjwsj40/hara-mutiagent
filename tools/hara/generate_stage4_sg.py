#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from hara_stage_merge import merge_stage_json
    from validate_hara_json import basic_normalize
except ImportError:  # pragma: no cover
    from .hara_stage_merge import merge_stage_json
    from .validate_hara_json import basic_normalize

OPERATION_MODE_PLACEHOLDERS = {"", "nan", "待Stage4模型填写", "待填写", "待补充", "待生成", "TODO", "todo"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def build_stage4(prefix: str, source: str, normalized: dict[str, Any]) -> dict[str, Any]:
    sg_sum = normalized.get("SG_Sum", [])
    operation_modes_to_fill = sum(
        1
        for row in sg_sum
        if str(row.get("操作模式") or "").strip() in OPERATION_MODE_PLACEHOLDERS
    )
    return {
        "meta": {
            "run_id": prefix,
            "stage": "stage4",
            "source": source,
            "generation": "deterministic_group_by_mf_and_safety_goal_highest_asil_min_ftti_except_operation_mode",
            "operation_mode_policy": "only 操作模式 is model-filled; rows are grouped within each MF by safety goal with highest ASIL and minimum FTTI",
            "operation_modes_to_fill": operation_modes_to_fill,
            "warnings_count": len(normalized.get("Validation_Warnings", [])),
        },
        "sg_sum": sg_sum,
        "review_log": [],
        "Validation_Warnings": normalized.get("Validation_Warnings", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Stage 4 SG_Sum grouped within each MF by safety goal; 操作模式 remains model-filled.")
    parser.add_argument("--json", help="Merged HARA JSON path. If omitted, --stage-dir and --prefix are required.")
    parser.add_argument("--stage-dir", help="Directory containing staged JSON files.")
    parser.add_argument("--prefix", help="Stage file prefix, for example EPB_HARA.")
    parser.add_argument("--out", required=True, help="Output stage4_sg_sum JSON path.")
    args = parser.parse_args()

    if args.json:
        merged = load_json(Path(args.json))
        source = str(args.json)
        prefix = args.prefix or Path(args.json).stem
    else:
        if not args.stage_dir or not args.prefix:
            raise SystemExit("Either --json or both --stage-dir and --prefix must be provided")
        merged = merge_stage_json(Path(args.stage_dir), args.prefix)
        source = str(args.stage_dir)
        prefix = args.prefix

    normalized = basic_normalize(merged)
    stage4 = build_stage4(prefix, source, normalized)
    dump_json(stage4, Path(args.out))
    print(json.dumps({
        "ok": True,
        "out": args.out,
        "sg_sum_rows": len(stage4["sg_sum"]),
        "operation_modes_to_fill": stage4["meta"]["operation_modes_to_fill"],
        "warnings": len(stage4["Validation_Warnings"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
