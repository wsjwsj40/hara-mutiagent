#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge Stage 2 single-function slice outputs into the final Stage 2 JSON."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from hara_schema_columns import MF_VEHICLE_HAZARDS_COLUMNS, get_by_alias, normalize_row
except ImportError:  # pragma: no cover
    from .hara_schema_columns import MF_VEHICLE_HAZARDS_COLUMNS, get_by_alias, normalize_row


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


def collect_input_paths(input_dir: Path | None, inputs: list[str] | None, run_id: str) -> list[Path]:
    explicit = [Path(item) for item in inputs or []]
    if explicit:
        return explicit
    if input_dir is None:
        raise SystemExit("Missing --inputs or --input-dir")
    final_name = f"{run_id}_stage2_mf_vehicle_hazards.json"
    paths = sorted(input_dir.glob(f"{run_id}_stage2_*_mf_vehicle_hazards.json"))
    return [path for path in paths if path.name != final_name]


def slice_function_id(data: Any, path: Path) -> str:
    if isinstance(data, dict) and isinstance(data.get("meta"), dict):
        fid = str(data["meta"].get("function_id") or data["meta"].get("Function_ID") or "").strip()
        if fid:
            return fid

    hazard_rows = rows(data, "mf_vehicle_hazards")
    if hazard_rows:
        fid = str(get_by_alias(hazard_rows[0], "Function_ID") or "").strip()
        if fid:
            return fid

    match = re.search(r"_stage2_([^_]+)_mf_vehicle_hazards\.json$", path.name)
    if match:
        return match.group(1)
    raise SystemExit(f"Unable to determine Function_ID for Stage2 slice: {path}")


def normalize_hazard_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_row(row, MF_VEHICLE_HAZARDS_COLUMNS)
    for key, value in row.items():
        if key not in normalized:
            normalized[key] = value
    return normalized


def replace_description_mf_id(description: Any, mf_id: str) -> str:
    text = str(description or "").strip()
    if not text:
        return f"{mf_id}："
    replaced = re.sub(r"^MF\d{3}\s*[:：]\s*", f"{mf_id}：", text)
    if replaced != text:
        return replaced
    return f"{mf_id}：{text}"


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


def merge_stage2(stage0_path: Path, slice_paths: list[Path], run_id: str) -> dict[str, Any]:
    stage0_data = load_json(stage0_path)
    stage0_rows = rows(stage0_data, "function_mapping")
    if not stage0_rows:
        raise SystemExit("Stage0 function_mapping is empty or missing.")

    expected_ids: list[str] = []
    stage0_names: dict[str, str] = {}
    for index, row in enumerate(stage0_rows, start=1):
        fid = function_id(row)
        if not fid:
            raise SystemExit(f"Stage0 row {index} is missing Function_ID.")
        expected_ids.append(fid)
        stage0_names[fid] = function_name(row)

    slices_by_fid: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in slice_paths:
        data = load_json(path)
        if not isinstance(data, dict):
            raise SystemExit(f"Stage2 slice top-level must be object: {path}")
        fid = slice_function_id(data, path)
        if fid in slices_by_fid:
            raise SystemExit(f"Duplicate Stage2 slice for Function_ID {fid}: {slices_by_fid[fid][0]} and {path}")
        slices_by_fid[fid] = (path, data)

    missing = [fid for fid in expected_ids if fid not in slices_by_fid]
    extra = sorted(fid for fid in slices_by_fid if fid not in stage0_names)
    if missing:
        raise SystemExit(f"Missing Stage2 slices for Function_ID: {', '.join(missing)}")
    if extra:
        raise SystemExit(f"Stage2 slices reference unknown Function_ID: {', '.join(extra)}")

    hazards: list[dict[str, Any]] = []
    hazard_reasoning: list[dict[str, Any]] = []
    review_log: list[Any] = []
    knowledge_evidence: list[Any] = []
    source_files: list[str] = []
    next_no = 1

    for stage1_row_index, fid in enumerate(expected_ids, start=1):
        path, data = slices_by_fid[fid]
        source_files.append(str(path))
        expected_name = stage0_names[fid]
        slice_hazards = rows(data, "mf_vehicle_hazards")
        slice_reasoning = rows(data, "hazard_reasoning")
        if len(slice_reasoning) != len(slice_hazards):
            raise SystemExit(f"hazard_reasoning count mismatch in {path}: expected {len(slice_hazards)}, actual {len(slice_reasoning)}")

        for local_index, source_row in enumerate(slice_hazards, start=1):
            mf_id = f"MF{next_no:03d}"
            row = normalize_hazard_row(source_row)
            row["No."] = next_no
            row["Milf_ID"] = mf_id
            row["Function_ID"] = fid
            row["source_function_name"] = expected_name
            row["Stage1_Row"] = stage1_row_index
            row["故障描述"] = replace_description_mf_id(get_by_alias(row, "故障描述"), mf_id)
            hazards.append(row)

            reasoning = dict(slice_reasoning[local_index - 1])
            reasoning["row"] = next_no
            reasoning["Milf_ID"] = mf_id
            hazard_reasoning.append(reasoning)
            next_no += 1

        review_log.extend(data.get("review_log", []) if isinstance(data.get("review_log"), list) else [])
        knowledge_evidence.extend(data.get("knowledge_evidence", []) if isinstance(data.get("knowledge_evidence"), list) else [])

    return {
        "meta": {
            "run_id": run_id,
            "stage": "stage2",
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "source_file": str(stage0_path),
            "source_slice_files": source_files,
            "knowledge_files_used": sorted({
                str(item.get("source"))
                for item in knowledge_evidence
                if isinstance(item, dict) and item.get("source")
            }),
        },
        "mf_vehicle_hazards": hazards,
        "hazard_reasoning": hazard_reasoning,
        "knowledge_evidence": dedupe_evidence(knowledge_evidence),
        "review_log": review_log,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge Stage2 single-function slice outputs.")
    parser.add_argument("--stage0", required=True, help="Stage0 function mapping JSON")
    parser.add_argument("--inputs", nargs="*", help="Explicit Stage2 slice JSON files")
    parser.add_argument("--input-dir", help="Directory containing <RUN_ID>_stage2_<Function_ID>_mf_vehicle_hazards.json files")
    parser.add_argument("--prefix", help="RUN_ID/prefix for discovering slice files")
    parser.add_argument("--out", required=True, help="Final Stage2 output path")
    args = parser.parse_args()

    stage0_path = Path(args.stage0)
    stage0_data = load_json(stage0_path)
    run_id = infer_run_id(args.prefix, stage0_path, stage0_data)
    slice_paths = collect_input_paths(Path(args.input_dir) if args.input_dir else None, args.inputs, run_id)
    if not slice_paths:
        raise SystemExit("No Stage2 slice files found.")

    merged = merge_stage2(stage0_path, slice_paths, run_id)
    dump_json(merged, Path(args.out))
    print(json.dumps({
        "ok": True,
        "stage": "stage2",
        "run_id": run_id,
        "input_slices": len(slice_paths),
        "mf_vehicle_hazards_rows": len(merged["mf_vehicle_hazards"]),
        "output": args.out,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
