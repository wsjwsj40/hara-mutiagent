#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge SEC batch results from independent Stage 3B agents."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from asil_matrix import asil_from_sec, normalize_sec
except ImportError:  # pragma: no cover
    from .asil_matrix import asil_from_sec, normalize_sec


def load_json(path: Path) -> Any:
    """Load JSON file with UTF-8 encoding."""
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Error parsing {path}: {exc.msg}")
    except FileNotFoundError:
        raise SystemExit(f"File not found: {path}")


def normalize_record_keys(record: dict) -> dict:
    """规范化记录中的字段名，去除多余空格。

    将 "S 评级推理" → "S评级推理"
    将 "E 评级推理" → "E评级推理"
    将 "C 评级推理" → "C评级推理"
    等等
    """
    normalized = {}
    for key, value in record.items():
        # 去除键名中的多余空格
        normalized_key = re.sub(r"\s+", "", key)
        normalized[normalized_key] = value
    return normalized


def get_field(record: dict[str, Any], field: str) -> Any:
    """获取字段值，尝试多种可能的键名变体。

    优先级：
    1. 精确匹配
    2. 去除空格后匹配
    3. 替换全角空格后匹配
    """
    # 精确匹配
    if field in record:
        return record[field]

    # 去除空格后匹配
    normalized_field = re.sub(r"\s+", "", field)
    normalized_record = normalize_record_keys(record)
    if normalized_field in normalized_record:
        return normalized_record[normalized_field]

    # 尝试常见的变体
    variants = [
        field,
        re.sub(r"\s+", "", field),  # 去除所有空格
        field.replace(" ", ""),    # 去除普通空格
        field.replace("　", ""),   # 去除全角空格
    ]

    for key in record.keys():
        for variant in variants:
            if re.sub(r"\s+", "", key) == variant:
                return record[key]

    return None


def load_batch_records(paths: list[str] | None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in paths or []:
        data = load_json(Path(path))
        if not isinstance(data, list):
            raise SystemExit(f"Expected JSON array in {path}")
        for index, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                raise SystemExit(f"Expected object at {path}[{index}]")
            records.append(item)
    return records


def sort_key(value: Any) -> tuple[int, Any]:
    try:
        return (0, int(str(value).strip()))
    except (TypeError, ValueError):
        return (1, str(value))


def index_records(records: list[dict[str, Any]], prefix: str) -> dict[Any, dict[str, Any]]:
    indexed: dict[Any, dict[str, Any]] = {}
    seen: dict[str, int] = {}
    for index, record in enumerate(records, start=1):
        list_no = get_field(record, "List_No")
        if list_no is None or str(list_no).strip() == "":
            key = f"__missing_{prefix}_{index}"
        else:
            normalized_key = str(list_no).strip()
            seen[normalized_key] = seen.get(normalized_key, 0) + 1
            key = list_no if seen[normalized_key] == 1 else f"{normalized_key}__duplicate_{prefix}_{seen[normalized_key]}"
        indexed[key] = record
    return indexed


def asil_display(s_value: Any, e_value: Any, c_value: Any) -> str:
    s_level = normalize_sec(s_value, "S")
    e_level = normalize_sec(e_value, "E")
    c_level = normalize_sec(c_value, "C")
    asil = asil_from_sec(s_value, e_value, c_value)
    if not (s_level and e_level and c_level and asil):
        return ""
    total = int(s_level[1:]) + int(e_level[1:]) + int(c_level[1:])
    asil_text = "QM" if asil == "QM" else f"ASIL {asil}"
    return f"{asil_text} ({s_level}+{e_level}+{c_level}={total})"


def merge_sec_records(
    s_records: list,
    e_records: list,
    c_records: list,
) -> list:
    """Merge S/E/C records by List_No without semantic validation."""
    s_by_no = index_records(s_records, "s")
    e_by_no = index_records(e_records, "e")
    c_by_no = index_records(c_records, "c")

    all_list_nos = set(s_by_no.keys()) | set(e_by_no.keys()) | set(c_by_no.keys())

    merged = []
    for list_no in sorted(all_list_nos, key=sort_key):
        s_rec = s_by_no.get(list_no, {})
        e_rec = e_by_no.get(list_no, {})
        c_rec = c_by_no.get(list_no, {})

        output_list_no = (
            get_field(s_rec, "List_No")
            or get_field(e_rec, "List_No")
            or get_field(c_rec, "List_No")
            or list_no
        )
        s_value = get_field(s_rec, "Severity 'S'") or ""
        e_value = get_field(e_rec, "暴露频率'E'") or ""
        c_value = get_field(c_rec, "控制能力 'C'") or ""

        # 使用 get_field 处理字段名中的多余空格
        sec_reasoning = {
            "S评级推理": get_field(s_rec, "S评级推理") or {},
            "E评级推理": get_field(e_rec, "E评级推理") or {},
            "C评级推理": get_field(c_rec, "C评级推理") or {},
        }

        merged.append({
            "List_No": output_list_no,
            "E-解释": get_field(e_rec, "E-解释") or "",
            "暴露频率'E'": e_value,
            "有风险的人员": get_field(s_rec, "有风险的人员") or "",
            "可能的后果('S'的理由)": get_field(s_rec, "可能的后果('S'的理由)") or "",
            "Severity 'S'": s_value,
            "C-解释": get_field(c_rec, "C-解释") or "",
            "控制能力 'C'": c_value,
            "结果ASIL": asil_display(s_value, e_value, c_value),
            "sec_reasoning": sec_reasoning,
        })

    return merged


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge SEC batch results from S/E/C independent rating agents"
    )
    parser.add_argument("--s-batches", nargs="+",
                        help="S rating batch JSON files")
    parser.add_argument("--e-batches", nargs="+",
                        help="E rating batch JSON files")
    parser.add_argument("--c-batches", nargs="+",
                        help="C rating batch JSON files")
    parser.add_argument("--safety",
                        help="Safety goal and safe state JSON file")
    parser.add_argument("--ftti",
                        help="(Deprecated) Single FTTI JSON file, use --ftti-batches instead")
    parser.add_argument("--ftti-batches", nargs="+",
                        help="FTTI batch JSON files")
    parser.add_argument("--output", required=True,
                        help="Output path for merged Stage 3B SEC JSON")
    parser.add_argument("--meta-mf-id", help="MF_ID for meta section")
    parser.add_argument("--meta-run-id", default="", help="Run ID for meta section")
    parser.add_argument("--cleanup", action="store_true",
                        help="Delete input batch files after successful merge")
    args = parser.parse_args()

    all_s_records = load_batch_records(args.s_batches)
    all_e_records = load_batch_records(args.e_batches)
    all_c_records = load_batch_records(args.c_batches)

    # Merge SEC records
    sec_records = merge_sec_records(all_s_records, all_e_records, all_c_records)

    # Build output structure
    output_data = {
        "meta": {
            "run_id": args.meta_run_id,
            "mf_id": args.meta_mf_id,
            "stage": "stage3b",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "sec_records": sec_records,
        "safety_goal": "",
        "safe_state": "",
    }

    # Merge safety_goal and safe_state
    if args.safety:
        safety_data = load_json(Path(args.safety))
        output_data["safety_goal"] = safety_data.get("safety_goal", "")
        output_data["safe_state"] = safety_data.get("safe_state", "")

    # Merge FTTI (支持批次文件或单个文件)
    all_ftti_records: list[dict[str, Any]] = []
    if args.ftti_batches:
        all_ftti_records.extend(load_batch_records(args.ftti_batches))
    elif args.ftti:
        all_ftti_records.extend(load_batch_records([args.ftti]))

    if all_ftti_records:
        ftti_by_no = {rec["List_No"]: rec for rec in all_ftti_records}

        for record in sec_records:
            list_no = record.get("List_No")
            ftti_rec = ftti_by_no.get(list_no)
            if ftti_rec:
                record["FTTI(ms)"] = ftti_rec.get("FTTI(ms)")
                record["FTTI理由"] = ftti_rec.get("FTTI理由", "")

    # Write output
    output_path = Path(args.output)
    output_path.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Get record count for printing
    record_count = len(sec_records)

    print(f"Merged {record_count} SEC records to {args.output}")

    # Cleanup input files
    if args.cleanup:
        all_input_files = (args.s_batches or []) + (args.e_batches or []) + (args.c_batches or [])
        if args.safety:
            all_input_files.append(args.safety)
        if args.ftti_batches:
            all_input_files.extend(args.ftti_batches)
        elif args.ftti:
            all_input_files.append(args.ftti)
        for file_path in all_input_files:
            Path(file_path).unlink()
            print(f"Deleted: {file_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
