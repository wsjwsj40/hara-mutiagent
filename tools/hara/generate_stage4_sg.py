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


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def build_stage4(prefix: str, source: str, normalized: dict[str, Any]) -> dict[str, Any]:
    return {
        "meta": {
            "run_id": prefix,
            "stage": "stage4_sg_sum",
            "source": source,
            "generation": "deterministic_from_corrected_hara_highest_asil",
            "warnings_count": len(normalized.get("Validation_Warnings", [])),
        },
        "sg_sum": normalized.get("SG_Sum", []),
        "review_log": [],
        "Validation_Warnings": normalized.get("Validation_Warnings", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Stage 4 SG_Sum deterministically from corrected HARA rows.")
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
        "warnings": len(stage4["Validation_Warnings"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
