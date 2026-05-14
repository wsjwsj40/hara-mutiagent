from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    from hara_schema_columns import (
        DERIVE_MF_COLUMNS,
        MF_VEHICLE_HAZARDS_COLUMNS,
        HARA_COLUMNS,
        SG_SUM_COLUMNS,
        normalize_rows,
    )
except ImportError:
    from .hara_schema_columns import (
        DERIVE_MF_COLUMNS,
        MF_VEHICLE_HAZARDS_COLUMNS,
        HARA_COLUMNS,
        SG_SUM_COLUMNS,
        normalize_rows,
    )

STAGE0_NAMES = ["function_mapping", "stage0_function_mapping", "mappings"]
STAGE1_NAMES = ["derive_mf", "DeriveMF", "deriveMF", "rows", "data"]
STAGE2_NAMES = ["mf_vehicle_hazards", "MF and Vehicle Hazards", "vehicle_hazards", "hazard_mapping", "rows", "data"]
STAGE3_NAMES = ["hara", "HARA", "hara_rows", "HARA_rows", "scenarios", "scenario_rows", "analysis_rows", "result_rows", "rows", "data"]
STAGE4_NAMES = ["sg_sum", "SG_Sum", "safety_goals", "rows", "data"]

def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)

def dump_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []

def pick_rows(data: Any, candidate_keys: list[str]) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    for key in candidate_keys:
        if key in data:
            return [item for item in as_list(data[key]) if isinstance(item, dict)]
    for key in ["result", "output", "content"]:
        if key in data:
            rows = pick_rows(data[key], candidate_keys)
            if rows:
                return rows
    return []

def dedupe_rows(rows: list[dict[str, Any]], key_fields: list[str]) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for row in rows:
        key = tuple(str(row.get(field, "nan")).strip() for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result

def renumber_rows(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    for index, row in enumerate(rows, start=1):
        row[field] = str(index)
    return rows

def infer_prefix_from_stage_file(path: Path) -> str:
    name = path.name
    match = re.match(r"(.+?)_stage\d+", name)
    if match:
        return match.group(1)
    return path.stem

def collect_stage_files(stage_dir: Path, prefix: str) -> dict[str, list[Path]]:
    files = sorted(stage_dir.glob(f"{prefix}_stage*.json"))
    grouped = {"stage0": [], "stage1": [], "stage2": [], "stage3": [], "stage4": [], "review": []}
    for path in files:
        name = path.name
        if name.endswith("_review.json"):
            grouped["review"].append(path)
        elif "_stage0_" in name:
            grouped["stage0"].append(path)
        elif "_stage1_derive_mf" in name:
            grouped["stage1"].append(path)
        elif "_stage1" in name:
            if not any("_stage1_derive_mf" in p.name for p in files):
                grouped["stage1"].append(path)
        elif "_stage2_mf_vehicle_hazards" in name:
            grouped["stage2"].append(path)
        elif "_stage2" in name:
            if not any("_stage2_mf_vehicle_hazards" in p.name for p in files):
                grouped["stage2"].append(path)
        elif "_stage3_" in name and name.endswith("_hara.json"):
            grouped["stage3"].append(path)
        elif "_stage3" in name:
            grouped["stage3"].append(path)
        elif "_stage4_sg_sum" in name:
            grouped["stage4"].append(path)
        elif "_stage4" in name:
            if not any("_stage4_sg_sum" in p.name for p in files):
                grouped["stage4"].append(path)
    return grouped
def merge_stage_json(stage_dir: Path, prefix: str) -> dict[str, Any]:
    grouped = collect_stage_files(stage_dir, prefix)
    function_mapping: list[dict[str, Any]] = []
    derive_mf: list[dict[str, Any]] = []
    mf_vehicle_hazards: list[dict[str, Any]] = []
    hara: list[dict[str, Any]] = []
    sg_sum: list[dict[str, Any]] = []
    review_log: list[dict[str, Any]] = []
    source_files: list[str] = []

    for path in grouped["stage0"]:
        data = load_json(path)
        source_files.append(path.name)
        function_mapping.extend(pick_rows(data, STAGE0_NAMES))
        if isinstance(data, dict):
            review_log.extend(as_list(data.get("review_log")))

    for path in grouped["stage1"]:
        data = load_json(path)
        source_files.append(path.name)
        rows = pick_rows(data, STAGE1_NAMES)
        derive_mf.extend(normalize_rows(rows, DERIVE_MF_COLUMNS))
        if isinstance(data, dict):
            review_log.extend(as_list(data.get("review_log")))

    for path in grouped["stage2"]:
        data = load_json(path)
        source_files.append(path.name)
        rows = pick_rows(data, STAGE2_NAMES)
        mf_vehicle_hazards.extend(normalize_rows(rows, MF_VEHICLE_HAZARDS_COLUMNS))
        if isinstance(data, dict):
            review_log.extend(as_list(data.get("review_log")))

    for path in grouped["stage3"]:
        data = load_json(path)
        source_files.append(path.name)
        rows = pick_rows(data, STAGE3_NAMES)
        hara.extend(normalize_rows(rows, HARA_COLUMNS))
        if isinstance(data, dict):
            review_log.extend(as_list(data.get("review_log")))

    for path in grouped["stage4"]:
        data = load_json(path)
        source_files.append(path.name)
        rows = pick_rows(data, STAGE4_NAMES)
        sg_sum.extend(normalize_rows(rows, SG_SUM_COLUMNS))
        if isinstance(data, dict):
            review_log.extend(as_list(data.get("review_log")))

    for path in grouped["review"]:
        data = load_json(path)
        source_files.append(path.name)
        if isinstance(data, dict):
            review_log.extend(as_list(data.get("review_log")))

    derive_mf = dedupe_rows(derive_mf, ["No.", "子功能"])
    mf_vehicle_hazards = dedupe_rows(mf_vehicle_hazards, ["Milf_ID", "故障描述", "整车级危害"])
    hara = dedupe_rows(hara, ["List_No", "MF_ID", "危害事件"])
    hara = renumber_rows(hara, "List_No")
    sg_sum = dedupe_rows(sg_sum, ["SG_No", "MF_ID", "安全目标", "ASIL Level"])

    return {
        "meta": {
            "prefix": prefix,
            "source_files": source_files,
            "derive_mf_rows": len(derive_mf),
            "mf_vehicle_hazards_rows": len(mf_vehicle_hazards),
            "hara_rows": len(hara),
            "sg_sum_rows": len(sg_sum),
        },
        "function_mapping": function_mapping,
        "derive_mf": derive_mf,
        "mf_vehicle_hazards": mf_vehicle_hazards,
        "hara": hara,
        "sg_sum": sg_sum,
        "review_log": review_log,
    }
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-dir", required=True)
    parser.add_argument("--prefix", required=False)
    parser.add_argument("--stage-file", required=False)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    stage_dir = Path(args.stage_dir)
    prefix = args.prefix
    if not prefix and args.stage_file:
        prefix = infer_prefix_from_stage_file(Path(args.stage_file))
    if not prefix:
        raise SystemExit("Missing --prefix or --stage-file")

    merged = merge_stage_json(stage_dir, prefix)
    dump_json(merged, Path(args.out))
    print(json.dumps(merged["meta"], ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
