#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

def infer_prefix_from_stage_file(path: Path) -> str:
    stem = path.stem
    match = re.search(r"(.+?)(?:[._-]stage\d+)", stem, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return stem

def looks_like_stage_file(path: Path) -> bool:
    return bool(re.search(r"[._-]stage\d+", path.stem, flags=re.IGNORECASE))

def run(cmd: list[str]) -> int:
    print("[CMD] " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, text=True)
    return proc.returncode

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Merge staged HARA JSON files when needed, normalize JSON in basic/strict mode, "
            "and export multi-sheet Excel."
        )
    )
    parser.add_argument("--json", help="Full merged HARA JSON path, or any stage JSON path such as EPB_HARA_stage4_sg_sum.json")
    parser.add_argument("--stage-dir", help="Directory containing stage JSON files. When provided, merge stage files first.")
    parser.add_argument("--prefix", help="Stage file prefix, for example EPB_HARA. If omitted and --json is a stage file, inferred from filename.")
    parser.add_argument("--out", required=True, help="Excel output path")
    parser.add_argument("--mode", choices=["basic", "strict"], default="basic")
    parser.add_argument("--min-scenarios", type=int, default=10)
    parser.add_argument("--max-scenarios", type=int, default=20)
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    xlsx_path = Path(args.out)
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    json_path: Path | None = Path(args.json) if args.json else None
    stage_dir: Path | None = Path(args.stage_dir) if args.stage_dir else None
    prefix = args.prefix

    need_merge = False
    if stage_dir is not None:
        need_merge = True
    elif json_path is not None and json_path.is_dir():
        stage_dir = json_path
        need_merge = True
    elif json_path is not None and looks_like_stage_file(json_path):
        stage_dir = json_path.parent
        prefix = prefix or infer_prefix_from_stage_file(json_path)
        need_merge = True

    if need_merge:
        if stage_dir is None:
            raise SystemExit("stage_dir is required for staged JSON merge")
        merged_path = xlsx_path.with_suffix(".merged.json")
        merge_cmd = [
            sys.executable,
            str(here / "hara_stage_merge.py"),
            "--stage-dir",
            str(stage_dir),
            "--out",
            str(merged_path),
        ]
        if prefix:
            merge_cmd.extend(["--prefix", prefix])
        rc = run(merge_cmd)
        if rc != 0:
            return rc
        if not merged_path.exists():
            raise SystemExit(f"merge command finished but merged JSON not found: {merged_path}")
        json_path = merged_path

    if json_path is None:
        raise SystemExit("Either --json or --stage-dir must be provided")
    if not json_path.exists():
        raise SystemExit(f"input JSON not found: {json_path}")

    normalized_path = xlsx_path.with_suffix(".normalized.json")
    validate_cmd = [
        sys.executable,
        str(here / "validate_hara_json.py"),
        "--json",
        str(json_path),
        "--out",
        str(normalized_path),
        "--mode",
        args.mode,
        "--min-scenarios",
        str(args.min_scenarios),
        "--max-scenarios",
        str(args.max_scenarios),
    ]
    rc = run(validate_cmd)
    # Do not continue to Excel export if normalization failed. In basic mode it should not fail.
    if rc != 0:
        return rc
    if not normalized_path.exists():
        raise SystemExit(f"validate command finished but normalized JSON not found: {normalized_path}")
    export_cmd = [
        sys.executable,
        str(here / "hara_excel_export.py"),
        "--input",
        str(normalized_path),
        "--output",
        str(xlsx_path),
    ]
    rc = run(export_cmd)
    if rc != 0:
        return rc
    if not xlsx_path.exists():
        raise SystemExit(f"Excel export command finished but file not found: {xlsx_path}")
    print(f"[OK] Excel exists: {xlsx_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())