#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge Stage 1 single-function slice outputs into the final Stage 1 JSON."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from hara_schema_columns import DERIVE_MF_COLUMNS, get_by_alias, normalize_row
except ImportError:  # pragma: no cover
    from .hara_schema_columns import DERIVE_MF_COLUMNS, get_by_alias, normalize_row


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


def rows(data: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get(key), list):
        return [item for item in data[key] if isinstance(item, dict)]
    return []


def infer_run_id(prefix: str | None, stage0_path: Path, stage0_data: Any) -> str:
    if prefix:
        return prefix
    if isinstance(stage0_data, dict) and isinstance(stage0_data.get("meta"), dict):
        run_id = str(stage0_data["meta"].get("run_id") or "").strip()
        if run_id:
            return run_id
    match = re.match(r"(.+?)_stage0", stage0_path.name)
    if match:
        return match.group(1)
    return "HARA_RUN"


def function_id(row: dict[str, Any]) -> str:
    return str(row.get("Function_ID") or row.get("function_id") or "").strip()


def function_name(row: dict[str, Any]) -> str:
    return str(
        row.get("extracted_function_name")
        or row.get("function_name")
        or row.get("子功能")
        or ""
    ).strip()


def slice_function_id(data: Any, stage0_names: dict[str, str], path: Path) -> str:
    if isinstance(data, dict) and isinstance(data.get("meta"), dict):
        fid = str(data["meta"].get("function_id") or data["meta"].get("Function_ID") or "").strip()
        if fid:
            return fid

    derive_rows = rows(data, "derive_mf")
    if derive_rows:
        fid = str(derive_rows[0].get("Function_ID") or derive_rows[0].get("function_id") or "").strip()
        if fid:
            return fid
        name = str(get_by_alias(derive_rows[0], "子功能") or "").strip()
        matches = [candidate_fid for candidate_fid, candidate_name in stage0_names.items() if candidate_name == name]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise SystemExit(f"Ambiguous Stage1 slice function name in {path}: {name}")

    raise SystemExit(f"Unable to determine Function_ID for Stage1 slice: {path}")


def collect_input_paths(input_dir: Path | None, inputs: list[str] | None, run_id: str) -> list[Path]:
    explicit = [Path(item) for item in inputs or []]
    if explicit:
        return explicit
    if input_dir is None:
        raise SystemExit("Missing --inputs or --input-dir")
    final_name = f"{run_id}_stage1_derive_mf.json"
    paths = sorted(input_dir.glob(f"{run_id}_stage1_*_derive_mf.json"))
    return [path for path in paths if path.name != final_name]


def dedupe_evidence(items: list[Any]) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for item in items:
        key = json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, dict) else str(item)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def merge_stage1(stage0_path: Path, slice_paths: list[Path], run_id: str) -> dict[str, Any]:
    stage0_data = load_json(stage0_path)
    stage0_rows = rows(stage0_data, "function_mapping")
    if not stage0_rows:
        raise SystemExit("Stage0 function_mapping is empty or missing.")

    stage0_names: dict[str, str] = {}
    for index, row in enumerate(stage0_rows, start=1):
        fid = function_id(row)
        if not fid:
            raise SystemExit(f"Stage0 row {index} is missing Function_ID.")
        stage0_names[fid] = function_name(row)

    slices_by_fid: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in slice_paths:
        data = load_json(path)
        if not isinstance(data, dict):
            raise SystemExit(f"Stage1 slice top-level must be object: {path}")
        fid = slice_function_id(data, stage0_names, path)
        if fid in slices_by_fid:
            raise SystemExit(f"Duplicate Stage1 slice for Function_ID {fid}: {slices_by_fid[fid][0]} and {path}")
        slices_by_fid[fid] = (path, data)

    expected_ids = [function_id(row) for row in stage0_rows]
    missing = [fid for fid in expected_ids if fid not in slices_by_fid]
    extra = sorted(fid for fid in slices_by_fid if fid not in stage0_names)
    if missing:
        raise SystemExit(f"Missing Stage1 slices for Function_ID: {', '.join(missing)}")
    if extra:
        raise SystemExit(f"Stage1 slices reference unknown Function_ID: {', '.join(extra)}")

    derive_mf: list[dict[str, Any]] = []
    field_reasoning: list[dict[str, Any]] = []
    review_log: list[Any] = []
    knowledge_evidence: list[Any] = []
    source_files: list[str] = []

    for index, stage0_row in enumerate(stage0_rows, start=1):
        fid = function_id(stage0_row)
        expected_name = function_name(stage0_row)
        path, data = slices_by_fid[fid]
        source_files.append(str(path))

        slice_rows = rows(data, "derive_mf")
        if len(slice_rows) != 1:
            raise SystemExit(f"Stage1 slice must contain exactly one derive_mf row: {path}")
        row = normalize_row(slice_rows[0], DERIVE_MF_COLUMNS)
        actual_name = str(row.get("子功能") or "").strip()
        if expected_name and actual_name != expected_name:
            raise SystemExit(f"Function name mismatch for {fid} in {path}: expected {expected_name}, actual {actual_name}")
        row["No."] = index
        row["子功能"] = expected_name
        derive_mf.append(row)

        reasoning_rows = rows(data, "field_reasoning")
        if len(reasoning_rows) != 1:
            raise SystemExit(f"Stage1 slice must contain exactly one field_reasoning row: {path}")
        reasoning = dict(reasoning_rows[0])
        reasoning["row"] = index
        reasoning["子功能"] = expected_name
        field_reasoning.append(reasoning)

        review_log.extend(data.get("review_log", []) if isinstance(data.get("review_log"), list) else [])
        knowledge_evidence.extend(data.get("knowledge_evidence", []) if isinstance(data.get("knowledge_evidence"), list) else [])

    return {
        "meta": {
            "run_id": run_id,
            "stage": "stage1",
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "source_file": str(stage0_path),
            "source_slice_files": source_files,
            "knowledge_files_used": sorted({
                str(item.get("source"))
                for item in knowledge_evidence
                if isinstance(item, dict) and item.get("source")
            }),
        },
        "derive_mf": derive_mf,
        "field_reasoning": field_reasoning,
        "knowledge_evidence": dedupe_evidence(knowledge_evidence),
        "review_log": review_log,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge Stage1 single-function slice outputs.")
    parser.add_argument("--stage0", required=True, help="Stage0 function mapping JSON")
    parser.add_argument("--inputs", nargs="*", help="Explicit Stage1 slice JSON files")
    parser.add_argument("--input-dir", help="Directory containing <RUN_ID>_stage1_<Function_ID>_derive_mf.json files")
    parser.add_argument("--prefix", help="RUN_ID/prefix for discovering slice files")
    parser.add_argument("--out", required=True, help="Final Stage1 output path")
    args = parser.parse_args()

    stage0_path = Path(args.stage0)
    stage0_data = load_json(stage0_path)
    run_id = infer_run_id(args.prefix, stage0_path, stage0_data)
    slice_paths = collect_input_paths(Path(args.input_dir) if args.input_dir else None, args.inputs, run_id)
    if not slice_paths:
        raise SystemExit("No Stage1 slice files found.")

    merged = merge_stage1(stage0_path, slice_paths, run_id)
    dump_json(merged, Path(args.out))
    print(json.dumps({
        "ok": True,
        "stage": "stage1",
        "run_id": run_id,
        "input_slices": len(slice_paths),
        "derive_mf_rows": len(merged["derive_mf"]),
        "output": args.out,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
