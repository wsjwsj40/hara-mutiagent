#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prepare compact Stage 1 function-scoped context packages.

This tool does not perform malfunction reasoning. It slices the complete
Stage 0 function mapping into one small JSON context per Function_ID so each
Stage 1 worker can reason about exactly one function.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned or "UNKNOWN"


def build_context(
    stage0_path: Path,
    stage0_data: Any,
    function_row: dict[str, Any],
    index: int,
    total: int,
    run_id: str,
) -> dict[str, Any]:
    fid = function_id(function_row)
    return {
        "meta": {
            "run_id": run_id,
            "stage": "stage1_context",
            "function_id": fid,
            "function_index": index,
            "function_count": total,
            "source_files": {
                "stage0": str(stage0_path),
            },
            "expected_slice_output": f"output/{run_id}_stage1_{safe_name(fid)}_derive_mf.json",
        },
        "function": function_row,
        "stage0_meta": stage0_data.get("meta", {}) if isinstance(stage0_data, dict) else {},
        "context_policy": {
            "stage1_worker": "只基于本文件中的 function 行生成一个功能的故障，不要加载完整 Stage0。",
            "output": "输出一个 Stage1 单功能片段：derive_mf 一行，field_reasoning 一行。",
            "validation": "使用 check_stage_json.py --stage stage1_slice 校验单功能片段；Stage1R 逐功能评审后再合并并用 --stage stage1 校验完整文件。",
        },
    }


def selected_functions(stage0_data: Any, function_id_filter: str | None) -> list[tuple[int, dict[str, Any]]]:
    function_rows = rows(stage0_data, "function_mapping")
    if not function_rows:
        raise SystemExit("Stage0 function_mapping is empty or missing.")
    selected: list[tuple[int, dict[str, Any]]] = []
    for index, row in enumerate(function_rows, start=1):
        fid = function_id(row)
        if function_id_filter and fid != function_id_filter:
            continue
        if not fid:
            raise SystemExit(f"Stage0 row {index} is missing Function_ID.")
        selected.append((index, row))
    if function_id_filter and not selected:
        raise SystemExit(f"Function_ID not found in Stage0: {function_id_filter}")
    return selected


def default_context_path(out_dir: Path, run_id: str, fid: str) -> Path:
    return out_dir / f"{run_id}_stage1_context_{safe_name(fid)}.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Slice Stage0 into Stage1 function-scoped context JSON files.")
    parser.add_argument("--stage0", required=True, help="Stage0 function mapping JSON")
    parser.add_argument("--prefix", help="RUN_ID/prefix for output file names")
    parser.add_argument("--function-id", help="Only slice one Function_ID")
    parser.add_argument("--out", help="Output path when slicing one Function_ID")
    parser.add_argument("--out-dir", default="output", help="Output directory for context files")
    args = parser.parse_args()

    stage0_path = Path(args.stage0)
    stage0_data = load_json(stage0_path)
    run_id = infer_run_id(args.prefix, stage0_path, stage0_data)
    function_rows = rows(stage0_data, "function_mapping")
    selected = selected_functions(stage0_data, args.function_id)
    if args.out and len(selected) != 1:
        raise SystemExit("--out can only be used with --function-id or a Stage0 file containing one function.")

    output_paths: list[str] = []
    out_dir = Path(args.out_dir)
    total = len(function_rows)
    for index, row in selected:
        fid = function_id(row)
        context = build_context(stage0_path, stage0_data, row, index, total, run_id)
        out_path = Path(args.out) if args.out else default_context_path(out_dir, run_id, fid)
        dump_json(context, out_path)
        output_paths.append(str(out_path))

    print(json.dumps({
        "ok": True,
        "stage": "stage1_context",
        "run_id": run_id,
        "contexts": len(output_paths),
        "files": output_paths,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
