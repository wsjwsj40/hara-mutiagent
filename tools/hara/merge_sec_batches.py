#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge SEC batch results from S/E/C independent rating agents into complete Stage 3B output."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def load_json(path: Path) -> dict | list:
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


def get_field(record: dict, field: str) -> any:
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

    return None  # 未找到


def parse_asil_suffix(s_value: str, e_value: str, c_value: str) -> str:
    """Calculate ASIL from S/E/C suffix values using sum rule.

    S: S0=0, S1=1, S2=2, S3=3
    E: E0=0, E1=1, E2=2, E3=3, E4=4
    C: C0=0, C1=1, C2=2, C3=3

    Sum -> ASIL:
    0-2: QM, 3-4: ASIL A, 5: ASIL B, 6: ASIL C, 7: ASIL D
    """
    s_match = re.search(r"S(\d+)", str(s_value).upper())
    e_match = re.search(r"E(\d+)", str(e_value).upper())
    c_match = re.search(r"C(\d+)", str(c_value).upper())

    if not all([s_match, e_match, c_match]):
        return "QM"

    s_score = int(s_match.group(1))
    e_score = int(e_match.group(1))
    c_score = int(c_match.group(1))

    total = s_score + e_score + c_score

    if total <= 2:
        return "QM"
    elif total == 3:
        return "ASIL A"
    elif total == 4:
        return "ASIL B"
    elif total == 5:
        return "ASIL C"
    elif total >= 6:
        return "ASIL D"
    return "QM"


def merge_sec_records(
    s_records: list,
    e_records: list,
    c_records: list,
) -> list:
    """Merge S/E/C records by List_No and calculate ASIL."""
    s_by_no = {rec["List_No"]: rec for rec in s_records}
    e_by_no = {rec["List_No"]: rec for rec in e_records}
    c_by_no = {rec["List_No"]: rec for rec in c_records}

    all_list_nos = set(s_by_no.keys()) | set(e_by_no.keys()) | set(c_by_no.keys())

    merged = []
    for list_no in sorted(all_list_nos):
        s_rec = s_by_no.get(list_no, {})
        e_rec = e_by_no.get(list_no, {})
        c_rec = c_by_no.get(list_no, {})

        s_value = s_rec.get("Severity 'S'", "S0")
        e_value = e_rec.get("暴露频率'E'", "E0")
        c_value = c_rec.get("控制能力 'C'", "C0")

        asil = parse_asil_suffix(s_value, e_value, c_value)
        asil_display = f"{asil} ({s_value}+{e_value}+{c_value}={s_value[1]}{e_value[1]}{c_value[1]})"

        # 使用 get_field 处理字段名中的多余空格
        sec_reasoning = {
            "S评级推理": get_field(s_rec, "S评级推理") or {},
            "E评级推理": get_field(e_rec, "E评级推理") or {},
            "C评级推理": get_field(c_rec, "C评级推理") or {},
        }

        # 合并时优先使用非空值，允许 S/E/C 都输出相同字段
        # S 评级输出：List_No, 有风险的人员, 可能的后果('S'的理由), Severity 'S', S评级推理
        # E 评级输出：List_No, E-解释, 暴露频率'E', 有风险的人员, E评级推理
        # C 评级输出：List_No, C-解释, 控制能力 'C', C评级推理

        # 获取有风险的人员（优先从 S，其次从 E），使用 get_field 处理空格
        at_risk_persons = get_field(s_rec, "有风险的人员") or get_field(e_rec, "有风险的人员") or ""

        merged.append({
            "List_No": list_no,
            "E-解释": get_field(e_rec, "E-解释") or "",
            "暴露频率'E'": e_value,
            "有风险的人员": at_risk_persons,
            "可能的后果('S'的理由)": get_field(s_rec, "可能的后果('S'的理由)") or "",
            "Severity 'S'": s_value,
            "C-解释": get_field(c_rec, "C-解释") or "",
            "控制能力 'C'": c_value,
            "结果ASIL": asil_display,
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
                        help="FTTI JSON file")
    parser.add_argument("--output", required=True,
                        help="Output path for merged Stage 3B SEC JSON")
    parser.add_argument("--meta-mf-id", help="MF_ID for meta section")
    parser.add_argument("--meta-run-id", default="", help="Run ID for meta section")
    parser.add_argument("--cleanup", action="store_true",
                        help="Delete input batch files after successful merge")
    args = parser.parse_args()

    # Load S/E/C batch files
    all_s_records = []
    all_e_records = []
    all_c_records = []

    for s_path in args.s_batches or []:
        all_s_records.extend(load_json(Path(s_path)))
    for e_path in args.e_batches or []:
        all_e_records.extend(load_json(Path(e_path)))
    for c_path in args.c_batches or []:
        all_c_records.extend(load_json(Path(c_path)))

    # Merge SEC records
    sec_records = merge_sec_records(all_s_records, all_e_records, all_c_records)

    # Build output structure
    output_data = {
        "meta": {
            "run_id": args.meta_run_id,
            "mf_id": args.meta_mf_id,
            "stage": "stage3b",
        },
        "sec_records": sec_records,
    }

    # Merge safety_goal and safe_state
    if args.safety:
        safety_data = load_json(Path(args.safety))
        output_data["safety_goal"] = safety_data.get("safety_goal", "")
        output_data["safe_state"] = safety_data.get("safe_state", "")

    # Merge FTTI
    if args.ftti:
        ftti_records = load_json(Path(args.ftti))
        ftti_by_no = {rec["List_No"]: rec for rec in ftti_records}

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
        if args.ftti:
            all_input_files.append(args.ftti)
        for file_path in all_input_files:
            Path(file_path).unlink()
            print(f"Deleted: {file_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
