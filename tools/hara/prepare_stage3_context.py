#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prepare compact Stage 3 context packages.

This tool does not perform HARA reasoning. It only slices large stage files into
small, MF-scoped or batch-scoped JSON inputs so Stage 3 agents can stay focused.
MF contexts reuse Stage 1 function context files instead of re-splitting Stage 0.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DOMAIN_KEYWORDS = (
    "触发",
    "条件",
    "前置",
    "请求",
    "驾驶员",
    "车速",
    "速度",
    "km/h",
    "静止",
    "停车",
    "驻车",
    "泊车",
    "行驶",
    "释放",
    "拉起",
    "制动",
    "夹紧",
    "保持",
    "退出",
    "禁止",
    "不允许",
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def rows(data: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get(key), list):
        return [item for item in data[key] if isinstance(item, dict)]
    return []


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).lower()


def infer_run_id(prefix: str | None, *paths: Path) -> str:
    if prefix:
        return prefix
    for path in paths:
        match = re.match(r"(.+?)_stage\d", path.name)
        if match:
            return match.group(1)
    return "HARA_RUN"


def stage2_lookup(stage2_data: Any) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("Milf_ID", "")).strip(): row
        for row in rows(stage2_data, "mf_vehicle_hazards")
        if str(row.get("Milf_ID", "")).strip()
    }


def hazard_reasoning_lookup(stage2_data: Any) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in rows(stage2_data, "hazard_reasoning"):
        mf_id = str(item.get("Milf_ID", "")).strip()
        if mf_id:
            result[mf_id] = item
    return result


def function_name(row: dict[str, Any]) -> str:
    return str(
        row.get("extracted_function_name")
        or row.get("Function_Name")
        or row.get("功能名称")
        or ""
    ).strip()


def function_id(row: dict[str, Any]) -> str:
    return str(row.get("Function_ID") or row.get("function_id") or "").strip()


def mf_function_id(row: dict[str, Any]) -> str:
    return str(
        row.get("Function_ID")
        or row.get("source_function_id")
        or row.get("function_id")
        or ""
    ).strip()


def mf_function_name(row: dict[str, Any]) -> str:
    return str(
        row.get("source_function_name")
        or row.get("子功能")
        or row.get("Function_Name")
        or row.get("function_name")
        or ""
    ).strip()


def score_function_match(function_row: dict[str, Any], mf_row: dict[str, Any]) -> int:
    fault = clean_text(mf_row.get("故障描述"))
    remark = clean_text(mf_row.get("备注"))
    structured_name = clean_text(mf_function_name(mf_row))
    combined = f"{fault}{remark}{structured_name}"
    score = 0

    fid = clean_text(function_id(function_row))
    name = clean_text(function_name(function_row))
    section = clean_text(function_row.get("section_title"))
    mf_fid = clean_text(mf_function_id(mf_row))

    if fid and mf_fid and fid == mf_fid:
        score += 1000
    if fid and fid in combined:
        score += 100
    if name and structured_name and name == structured_name:
        score += 500
    if name and name in combined:
        score += 80
    if section and section in combined:
        score += 40

    # Loose token overlap helps when Stage 2 descriptions shorten the function name.
    for token in re.split(r"[、，,；;（）()\\s]+", function_name(function_row)):
        token = token.strip()
        if len(token) >= 3 and clean_text(token) in combined:
            score += 8

    return score


def pick_matched_functions(stage0_data: Any, mf_row: dict[str, Any], max_items: int = 3) -> list[dict[str, Any]]:
    scored: list[tuple[int, dict[str, Any]]] = []
    for row in rows(stage0_data, "function_mapping"):
        score = score_function_match(row, mf_row)
        if score > 0:
            scored.append((score, row))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [row for _score, row in scored[:max_items]]


def match_warnings(mf_row: dict[str, Any], matched_functions: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    if not matched_functions:
        warnings.append("未找到功能背景，无法可靠提取 detail_text。请检查 Stage1 context 文件或 Stage2 的 Function_ID/source_function_name。")
        return warnings
    if not mf_function_id(mf_row):
        warnings.append("Stage2 当前 MF 缺少 Function_ID/source_function_id，无法直接定位 Stage1 context，可能退回到功能名文本匹配。")
    if not any(str(row.get("detail_text", "")).strip() for row in matched_functions):
        warnings.append("已匹配功能背景，但缺少 detail_text。")
    if len(matched_functions) > 1 and not mf_function_id(mf_row):
        warnings.append("文本匹配到多个候选 Stage0 功能，请由 Stage3A 子 agent 复核 matched_functions。")
    return warnings


def extract_domain_hints(function_rows: list[dict[str, Any]]) -> dict[str, Any]:
    snippets: list[str] = []
    text_blocks: list[str] = []
    for row in function_rows:
        for field in ("detail_text", "function_description", "remark", "source_evidence"):
            value = str(row.get(field, "")).strip()
            if value:
                text_blocks.append(value)

    for text in text_blocks:
        lines = [line.strip() for line in re.split(r"[\r\n]+", text) if line.strip()]
        if len(lines) <= 1:
            lines = re.split(r"[。；;]", text)
        for line in lines:
            if any(keyword in line for keyword in DOMAIN_KEYWORDS):
                normalized = line.strip()
                if normalized and normalized not in snippets:
                    snippets.append(normalized)
            if len(snippets) >= 20:
                break
        if len(snippets) >= 20:
            break

    full_text = "\n".join(text_blocks)
    return {
        "hints": snippets,
        "has_stationary_hint": any(word in full_text for word in ("静止", "停车", "驻车", "泊车")),
        "has_driving_hint": any(word in full_text for word in ("行驶", "动态", "巡航", "变道", "加速", "减速")),
        "has_driver_request_hint": any(word in full_text for word in ("驾驶员请求", "驾驶员操作", "开关", "手动")),
        "detected_speed_limits": sorted(set(re.findall(r"(?:≤|<=|<|小于等于|不超过|低于)\s*\d+(?:\.\d+)?\s*km/?h", full_text))),
    }


def compact_function(row: dict[str, Any], include_detail: bool) -> dict[str, Any]:
    result = {
        "Function_ID": function_id(row),
        "extracted_function_name": function_name(row),
        "function_category": row.get("function_category"),
        "section_id": row.get("section_id"),
        "section_title": row.get("section_title"),
        "system_hint": row.get("system_hint"),
        "matched_system": row.get("matched_system"),
        "remark": row.get("remark"),
    }
    if include_detail:
        result["detail_text"] = row.get("detail_text")
    return result


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned or "UNKNOWN"


def stage1_context_path(stage1_context_dir: Path, run_id: str, fid: str) -> Path:
    return stage1_context_dir / f"{run_id}_stage1_context_{safe_name(fid)}.json"


def load_function_context(
    stage1_context_dir: Path | None,
    run_id: str,
    fid: str,
    stage0_data: Any | None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], str | None]:
    if stage1_context_dir and fid:
        path = stage1_context_path(stage1_context_dir, run_id, fid)
        if path.exists():
            context = load_json(path)
            function_row = context.get("function") if isinstance(context, dict) else None
            if isinstance(function_row, dict):
                return context, [function_row], str(path)

    if stage0_data is not None:
        for row in rows(stage0_data, "function_mapping"):
            if function_id(row) == fid:
                return None, [row], None
    return None, [], None


def build_mf_context(
    stage2_path: Path,
    mf_id: str,
    stage1_context_dir: Path | None = None,
    stage0_path: Path | None = None,
    prefix: str | None = None,
) -> dict[str, Any]:
    stage0_data = load_json(stage0_path) if stage0_path else None
    stage2_data = load_json(stage2_path)
    mf_rows = stage2_lookup(stage2_data)
    if mf_id not in mf_rows:
        raise SystemExit(f"MF_ID not found in Stage 2: {mf_id}")

    mf_row = mf_rows[mf_id]
    run_id = infer_run_id(prefix, stage2_path, stage0_path) if stage0_path else infer_run_id(prefix, stage2_path)
    fid = mf_function_id(mf_row)
    function_context, matched_functions, function_context_file = load_function_context(stage1_context_dir, run_id, fid, stage0_data)
    if not matched_functions and stage0_data is not None:
        matched_functions = pick_matched_functions(stage0_data, mf_row)
    warnings = match_warnings(mf_row, matched_functions)
    if not matched_functions:
        raise SystemExit(
            f"Unable to find function background for {mf_id}. "
            "Provide --stage1-context-dir containing stage1_context_<Function_ID>.json, "
            "or pass --stage0 as fallback."
        )
    hazard_reasoning = hazard_reasoning_lookup(stage2_data).get(mf_id)

    source_files: dict[str, str] = {"stage2": str(stage2_path)}
    if function_context_file:
        source_files["stage1_context"] = function_context_file
    if stage0_path:
        source_files["stage0_fallback"] = str(stage0_path)

    return {
        "meta": {
            "run_id": run_id,
            "stage": "stage3_context",
            "mf_id": mf_id,
            "function_id": fid,
            "source_files": source_files,
            "matched_function_count": len(matched_functions),
            "traceability_warnings": warnings,
        },
        "mf": mf_row,
        "hazard_reasoning": hazard_reasoning,
        "function_context": function_context,
        "matched_functions": [
            compact_function(row, include_detail=function_context is None)
            for row in matched_functions
        ],
        "operating_domain_hints": extract_domain_hints(matched_functions),
        "context_policy": {
            "stage3a": "只读取本文件、Stage3A 规则和 operation_scenarios.json；不要读取完整 Stage0/Stage2。",
            "stage3ar": "只读取 Stage3A 当前 MF 文件、本文件摘要和场景评审规则；不要读取 SEC 评级知识库。",
            "stage3b": "只读取 Stage3A 当前 MF 文件、本文件摘要和必要风险评估章节。",
            "stage3br": "只读取 Stage3A/Stage3B 当前 MF 文件、本文件摘要和 SEC 评审规则。",
        },
    }


def context_brief(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "mf": context.get("mf"),
        "hazard_reasoning": context.get("hazard_reasoning"),
        "matched_functions": [
            compact_function(row, include_detail=False)
            for row in context.get("matched_functions", [])
            if isinstance(row, dict)
        ],
        "operating_domain_hints": context.get("operating_domain_hints"),
    }


def chunks(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def write_mf_context(args: argparse.Namespace) -> None:
    stage2_path = Path(args.stage2)
    stage0_path = Path(args.stage0) if args.stage0 else None
    stage1_context_dir = Path(args.stage1_context_dir) if args.stage1_context_dir else None
    if args.all:
        data = load_json(stage2_path)
        mf_ids = sorted(stage2_lookup(data))
        if not mf_ids:
            raise SystemExit("No MF_ID found in Stage 2")
        out_dir = Path(args.out_dir)
        run_id = infer_run_id(args.prefix, stage2_path, stage0_path) if stage0_path else infer_run_id(args.prefix, stage2_path)
        for mf_id in mf_ids:
            context = build_mf_context(stage2_path, mf_id, stage1_context_dir, stage0_path, args.prefix)
            out = out_dir / f"{run_id}_stage3_context_{mf_id}.json"
            dump_json(context, out)
            print(out)
        return

    if not args.mf_id:
        raise SystemExit("mf-context requires --mf-id or --all")
    context = build_mf_context(stage2_path, args.mf_id, stage1_context_dir, stage0_path, args.prefix)
    out = Path(args.out) if args.out else Path(args.out_dir) / f"{context['meta']['run_id']}_stage3_context_{args.mf_id}.json"
    dump_json(context, out)
    print(out)


def write_sec_batches(args: argparse.Namespace) -> None:
    context_path = Path(args.context)
    stage3a_path = Path(args.stage3a)
    context = load_json(context_path)
    stage3a = load_json(stage3a_path)
    scenarios = rows(stage3a, "scenarios")
    if not scenarios:
        raise SystemExit("No scenarios found in Stage 3A file")

    batch_size = max(1, args.batch_size)
    batches = chunks(scenarios, batch_size)
    meta = context.get("meta", {})
    run_id = str(meta.get("run_id") or infer_run_id(args.prefix, stage3a_path, context_path))
    mf_id = str(meta.get("mf_id") or args.mf_id or "")
    if not mf_id:
        raise SystemExit("Missing MF_ID in context; pass --mf-id")

    out_dir = Path(args.out_dir)
    for index, batch in enumerate(batches, start=1):
        data = {
            "meta": {
                "run_id": run_id,
                "stage": "stage3b_batch_context",
                "mf_id": mf_id,
                "batch_index": index,
                "batch_count": len(batches),
                "batch_size": len(batch),
                "total_scenarios": len(scenarios),
                "source_files": {
                    "stage3_context": str(context_path),
                    "stage3a": str(stage3a_path),
                },
            },
            "mf_context": context_brief(context),
            "max_asil_planning": stage3a.get("max_asil_planning"),
            "scenarios": batch,
            "output_instruction": "本文件供 Stage3B 的 S/E/C 分离子任务使用。S 子任务只输出 S JSON 数组，E 子任务只输出 E JSON 数组，C 子任务只输出 C JSON 数组；不要输出 Markdown 或解释文字。",
        }
        out = out_dir / f"{run_id}_stage3b_{mf_id}_batch{index:02d}_context.json"
        dump_json(data, out)
        print(out)


def list_no_key(row: dict[str, Any]) -> str:
    return str(row.get("List_No") or row.get("List No") or row.get("ListNo") or "").strip()


def write_stage3a_review_batches(args: argparse.Namespace) -> None:
    context_path = Path(args.context)
    stage3a_path = Path(args.stage3a)
    context = load_json(context_path)
    stage3a = load_json(stage3a_path)
    scenarios = rows(stage3a, "scenarios")
    if not scenarios:
        raise SystemExit("No scenarios found in Stage 3A file")

    batch_size = max(1, args.batch_size)
    batches = chunks(scenarios, batch_size)
    meta = context.get("meta", {})
    run_id = str(meta.get("run_id") or infer_run_id(args.prefix, stage3a_path, context_path))
    mf_id = str(meta.get("mf_id") or args.mf_id or "")
    if not mf_id:
        raise SystemExit("Missing MF_ID in context; pass --mf-id")

    out_dir = Path(args.out_dir)
    for index, batch in enumerate(batches, start=1):
        data = {
            "meta": {
                "run_id": run_id,
                "stage": "stage3ar_batch_context",
                "mf_id": mf_id,
                "batch_index": index,
                "batch_count": len(batches),
                "batch_size": len(batch),
                "total_scenarios": len(scenarios),
                "source_files": {
                    "stage3_context": str(context_path),
                    "stage3a": str(stage3a_path),
                },
            },
            "mf_context": context_brief(context),
            "max_asil_planning": stage3a.get("max_asil_planning"),
            "scenarios": batch,
            "output_instruction": "只评审 Stage3A 场景和危害事件；不要判断 S/E/C、ASIL、FTTI 或安全目标。输出本批 review JSON 数组。",
        }
        out = out_dir / f"{run_id}_stage3ar_{mf_id}_batch{index:02d}_context.json"
        dump_json(data, out)
        print(out)


def write_stage3b_review_batches(args: argparse.Namespace) -> None:
    context_path = Path(args.context)
    stage3a_path = Path(args.stage3a)
    stage3b_path = Path(args.stage3b)
    context = load_json(context_path)
    stage3a = load_json(stage3a_path)
    stage3b = load_json(stage3b_path)
    scenarios = rows(stage3a, "scenarios")
    sec_records = rows(stage3b, "sec_records")
    if not scenarios:
        raise SystemExit("No scenarios found in Stage 3A file")
    if not sec_records:
        raise SystemExit("No sec_records found in Stage 3B file")

    sec_by_list_no = {list_no_key(row): row for row in sec_records if list_no_key(row)}
    review_items = [
        {
            "scenario": scenario,
            "sec_record": sec_by_list_no.get(list_no_key(scenario)),
        }
        for scenario in scenarios
    ]

    batch_size = max(1, args.batch_size)
    batches = chunks(review_items, batch_size)
    meta = context.get("meta", {})
    run_id = str(meta.get("run_id") or infer_run_id(args.prefix, stage3a_path, stage3b_path, context_path))
    mf_id = str(meta.get("mf_id") or args.mf_id or "")
    if not mf_id:
        raise SystemExit("Missing MF_ID in context; pass --mf-id")

    out_dir = Path(args.out_dir)
    for index, batch in enumerate(batches, start=1):
        data = {
            "meta": {
                "run_id": run_id,
                "stage": "stage3br_batch_context",
                "mf_id": mf_id,
                "batch_index": index,
                "batch_count": len(batches),
                "batch_size": len(batch),
                "total_scenarios": len(scenarios),
                "source_files": {
                    "stage3_context": str(context_path),
                    "stage3a": str(stage3a_path),
                    "stage3b": str(stage3b_path),
                },
            },
            "mf_context": context_brief(context),
            "max_asil_planning": stage3a.get("max_asil_planning"),
            "safety_goal": stage3b.get("safety_goal"),
            "safe_state": stage3b.get("safe_state"),
            "items": batch,
            "output_instruction": "只评审 Stage3B SEC、FTTI、安全目标和安全状态；场景质量问题应退回 Stage3AR。输出本批 review JSON 数组。",
        }
        out = out_dir / f"{run_id}_stage3br_{mf_id}_batch{index:02d}_context.json"
        dump_json(data, out)
        print(out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare compact Stage 3 context packages.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    mf = subparsers.add_parser("mf-context", help="Build one MF-scoped Stage 3 context package.")
    mf.add_argument("--stage0", help="Optional Stage0 fallback when stage1 context files are unavailable")
    mf.add_argument("--stage2", required=True)
    mf.add_argument("--stage1-context-dir", default="output", help="Directory containing <RUN_ID>_stage1_context_<Function_ID>.json")
    mf.add_argument("--mf-id")
    mf.add_argument("--all", action="store_true")
    mf.add_argument("--prefix")
    mf.add_argument("--out")
    mf.add_argument("--out-dir", default="output")
    mf.set_defaults(func=write_mf_context)

    sec = subparsers.add_parser("sec-batches", help="Split Stage 3A scenarios into Stage 3B batch context files.")
    sec.add_argument("--context", required=True)
    sec.add_argument("--stage3a", required=True)
    sec.add_argument("--mf-id")
    sec.add_argument("--prefix")
    sec.add_argument("--out-dir", default="output")
    sec.add_argument("--batch-size", type=int, default=5)
    sec.set_defaults(func=write_sec_batches)

    ar = subparsers.add_parser("stage3a-review-batches", help="Split Stage 3A scenarios into Stage 3AR review batch context files.")
    ar.add_argument("--context", required=True)
    ar.add_argument("--stage3a", required=True)
    ar.add_argument("--mf-id")
    ar.add_argument("--prefix")
    ar.add_argument("--out-dir", default="output")
    ar.add_argument("--batch-size", type=int, default=5)
    ar.set_defaults(func=write_stage3a_review_batches)

    br = subparsers.add_parser("stage3b-review-batches", help="Split Stage 3A/3B paired rows into Stage 3BR review batch context files.")
    br.add_argument("--context", required=True)
    br.add_argument("--stage3a", required=True)
    br.add_argument("--stage3b", required=True)
    br.add_argument("--mf-id")
    br.add_argument("--prefix")
    br.add_argument("--out-dir", default="output")
    br.add_argument("--batch-size", type=int, default=5)
    br.set_defaults(func=write_stage3b_review_batches)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
