#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge Stage 2R single-function review JSON files into one review JSON."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Error parsing {path}: {exc.msg}")
    except FileNotFoundError:
        raise SystemExit(f"File not found: {path}")


def dump_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def rows(data: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get(key), list):
        return [item for item in data[key] if isinstance(item, dict)]
    return []


def infer_run_id(prefix: str | None, paths: list[Path]) -> str:
    if prefix:
        return prefix
    for path in paths:
        match = re.match(r"(.+?)_stage2_", path.name)
        if match:
            return match.group(1)
    return "HARA_RUN"


def collect_input_paths(input_dir: Path | None, inputs: list[str] | None, run_id: str | None) -> list[Path]:
    explicit = [Path(item) for item in inputs or []]
    if explicit:
        return explicit
    if input_dir is None:
        raise SystemExit("Missing --inputs or --input-dir")
    pattern = f"{run_id}_stage2_*_review.json" if run_id else "*_stage2_*_review.json"
    return [
        path
        for path in sorted(input_dir.glob(pattern))
        if not path.name.endswith("_stage2_review.json")
    ]


def function_id(data: Any, path: Path) -> str:
    if isinstance(data, dict) and isinstance(data.get("meta"), dict):
        fid = str(data["meta"].get("function_id") or data["meta"].get("Function_ID") or "").strip()
        if fid:
            return fid
    match = re.search(r"_stage2_([^_]+)_review\.json$", path.name)
    if match:
        return match.group(1)
    raise SystemExit(f"Unable to determine Function_ID for review slice: {path}")


def stage0_function_id(row: dict[str, Any]) -> str:
    return str(row.get("Function_ID") or row.get("function_id") or "").strip()


def expected_function_ids(stage0_data: Any | None) -> list[str]:
    if stage0_data is None:
        return []
    function_rows = rows(stage0_data, "function_mapping")
    if not function_rows:
        raise SystemExit("Stage0 function_mapping is empty or missing.")
    expected: list[str] = []
    for index, row in enumerate(function_rows, start=1):
        fid = stage0_function_id(row)
        if not fid:
            raise SystemExit(f"Stage0 row {index} is missing Function_ID.")
        expected.append(fid)
    return expected


def merge_reviews(paths: list[Path], run_id: str, stage0_data: Any | None = None) -> dict[str, Any]:
    issues: list[Any] = []
    fixes: list[Any] = []
    review_log: list[Any] = []
    source_files: list[str] = []
    results: list[str] = []
    seen_functions: set[str] = set()

    for path in paths:
        data = load_json(path)
        if not isinstance(data, dict):
            raise SystemExit(f"Review slice top-level must be object: {path}")
        fid = function_id(data, path)
        if fid in seen_functions:
            raise SystemExit(f"Duplicate Stage2R review slice for Function_ID {fid}: {path}")
        seen_functions.add(fid)
        source_files.append(str(path))

        result = str(data.get("overall_result") or data.get("result") or "").strip().lower()
        if result:
            results.append(result)

        for issue in as_list(data.get("issues")):
            if isinstance(issue, dict):
                issue = dict(issue)
                issue.setdefault("function_id", fid)
            issues.append(issue)
        for fix in as_list(data.get("fixes")):
            if isinstance(fix, dict):
                fix = dict(fix)
                fix.setdefault("function_id", fid)
            fixes.append(fix)
        review_log.extend(as_list(data.get("review_log")))

    expected_ids = expected_function_ids(stage0_data)
    if expected_ids:
        missing = [fid for fid in expected_ids if fid not in seen_functions]
        extra = sorted(fid for fid in seen_functions if fid not in expected_ids)
        if missing:
            raise SystemExit(f"Missing Stage2R review slices for Function_ID: {', '.join(missing)}")
        if extra:
            raise SystemExit(f"Stage2R review slices reference unknown Function_ID: {', '.join(extra)}")
        reviewed_ids = expected_ids
    else:
        reviewed_ids = sorted(seen_functions)

    overall = "failed" if any(result == "failed" for result in results) else "pass"
    return {
        "meta": {
            "run_id": run_id,
            "stage": "stage2_review",
            "target_file": f"output/{run_id}_stage2_mf_vehicle_hazards.json",
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "source_review_files": source_files,
            "reviewed_function_ids": reviewed_ids,
            "function_count": len(reviewed_ids),
        },
        "overall_result": overall,
        "issues": issues,
        "fixes": fixes,
        "review_log": review_log,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge Stage2R single-function review JSON files.")
    parser.add_argument("--inputs", nargs="*", help="Explicit Stage2R review slice files")
    parser.add_argument("--input-dir", help="Directory containing <RUN_ID>_stage2_<Function_ID>_review.json files")
    parser.add_argument("--stage0", help="Optional Stage0 JSON for Function_ID completeness checks")
    parser.add_argument("--prefix", help="RUN_ID/prefix for discovering files")
    parser.add_argument("--out", required=True, help="Merged Stage2R review output path")
    args = parser.parse_args()

    input_dir = Path(args.input_dir) if args.input_dir else None
    paths = collect_input_paths(input_dir, args.inputs, args.prefix)
    if not paths:
        raise SystemExit("No Stage2R review slice files found.")
    run_id = infer_run_id(args.prefix, paths)
    stage0_data = load_json(Path(args.stage0)) if args.stage0 else None
    merged = merge_reviews(paths, run_id, stage0_data)
    dump_json(merged, Path(args.out))
    print(json.dumps({
        "ok": True,
        "stage": "stage2_review",
        "run_id": run_id,
        "input_reviews": len(paths),
        "overall_result": merged["overall_result"],
        "output": args.out,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
