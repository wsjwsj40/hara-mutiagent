#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prepare compact Stage 3 context packages.

This tool does not perform HARA reasoning. It only slices large stage files into
small, MF-scoped or batch-scoped JSON inputs so Stage 3 agents can stay focused.
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
        warnings.append("未匹配到 Stage0 功能，无法可靠提取 detail_text。请检查 Stage2 是否包含 Function_ID/source_function_name。")
        return warnings
    if not mf_function_id(mf_row):
        warnings.append("Stage2 当前 MF 缺少 Function_ID/source_function_id，已退回到功能名文本匹配。")
    if not any(str(row.get("detail_text", "")).strip() for row in matched_functions):
        warnings.append("已匹配 Stage0 功能，但匹配行缺少 detail_text。")
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


def build_mf_context(
    stage0_path: Path,
    stage2_path: Path,
    mf_id: str,
    prefix: str | None = None,
) -> dict[str, Any]:
    stage0_data = load_json(stage0_path)
    stage2_data = load_json(stage2_path)
    mf_rows = stage2_lookup(stage2_data)
    if mf_id not in mf_rows:
        raise SystemExit(f"MF_ID not found in Stage 2: {mf_id}")

    mf_row = mf_rows[mf_id]
    matched_functions = pick_matched_functions(stage0_data, mf_row)
    warnings = match_warnings(mf_row, matched_functions)
    if not matched_functions:
        raise SystemExit(f"Unable to match Stage0 function for {mf_id}. Add Function_ID/source_function_name to Stage2.")
    hazard_reasoning = hazard_reasoning_lookup(stage2_data).get(mf_id)
    run_id = infer_run_id(prefix, stage2_path, stage0_path)

    return {
        "meta": {
            "run_id": run_id,
            "stage": "stage3_context",
            "mf_id": mf_id,
            "source_files": {
                "stage0": str(stage0_path),
                "stage2": str(stage2_path),
            },
            "matched_function_count": len(matched_functions),
            "traceability_warnings": warnings,
        },
        "mf": mf_row,
        "hazard_reasoning": hazard_reasoning,
        "matched_functions": [compact_function(row, include_detail=True) for row in matched_functions],
        "operating_domain_hints": extract_domain_hints(matched_functions),
        "context_policy": {
            "stage3a": "只读取本文件、Stage3A 规则和 operation_scenarios.json；不要读取完整 Stage0/Stage2。",
            "stage3b": "只读取 Stage3A 当前 MF 文件、本文件摘要和必要风险评估章节。",
            "stage3r": "只读取合并后的当前 MF HARA、本文件摘要和必要评审规则。",
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
    stage0_path = Path(args.stage0)
    stage2_path = Path(args.stage2)
    if args.all:
        data = load_json(stage2_path)
        mf_ids = sorted(stage2_lookup(data))
        if not mf_ids:
            raise SystemExit("No MF_ID found in Stage 2")
        out_dir = Path(args.out_dir)
        run_id = infer_run_id(args.prefix, stage2_path, stage0_path)
        for mf_id in mf_ids:
            context = build_mf_context(stage0_path, stage2_path, mf_id, args.prefix)
            out = out_dir / f"{run_id}_stage3_context_{mf_id}.json"
            dump_json(context, out)
            print(out)
        return

    if not args.mf_id:
        raise SystemExit("mf-context requires --mf-id or --all")
    context = build_mf_context(stage0_path, stage2_path, args.mf_id, args.prefix)
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


def write_review_batches(args: argparse.Namespace) -> None:
    context_path = Path(args.context)
    stage3_path = Path(args.stage3)
    context = load_json(context_path)
    stage3 = load_json(stage3_path)
    hara_rows = rows(stage3, "hara")
    if not hara_rows:
        raise SystemExit("No hara rows found in Stage 3 file")

    batch_size = max(1, args.batch_size)
    batches = chunks(hara_rows, batch_size)
    meta = context.get("meta", {})
    run_id = str(meta.get("run_id") or infer_run_id(args.prefix, stage3_path, context_path))
    mf_id = str(meta.get("mf_id") or args.mf_id or "")
    if not mf_id:
        raise SystemExit("Missing MF_ID in context; pass --mf-id")

    out_dir = Path(args.out_dir)
    for index, batch in enumerate(batches, start=1):
        data = {
            "meta": {
                "run_id": run_id,
                "stage": "stage3r_batch_context",
                "mf_id": mf_id,
                "batch_index": index,
                "batch_count": len(batches),
                "batch_size": len(batch),
                "total_scenarios": len(hara_rows),
                "source_files": {
                    "stage3_context": str(context_path),
                    "stage3": str(stage3_path),
                },
            },
            "mf_context": context_brief(context),
            "max_asil_planning": stage3.get("max_asil_planning"),
            "safety_goal": stage3.get("safety_goal"),
            "safe_state": stage3.get("safe_state"),
            "hara": batch,
            "output_instruction": "只输出本批 per_scenario_reviews 的 JSON 数组；不要输出 Markdown 或解释文字。",
        }
        out = out_dir / f"{run_id}_stage3r_{mf_id}_batch{index:02d}_context.json"
        dump_json(data, out)
        print(out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare compact Stage 3 context packages.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    mf = subparsers.add_parser("mf-context", help="Build one MF-scoped Stage 3 context package.")
    mf.add_argument("--stage0", required=True)
    mf.add_argument("--stage2", required=True)
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

    review = subparsers.add_parser("review-batches", help="Split merged Stage 3 HARA into Stage 3R batch context files.")
    review.add_argument("--context", required=True)
    review.add_argument("--stage3", required=True)
    review.add_argument("--mf-id")
    review.add_argument("--prefix")
    review.add_argument("--out-dir", default="output")
    review.add_argument("--batch-size", type=int, default=5)
    review.set_defaults(func=write_review_batches)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
