#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIL utilities for HARA.

The final ASIL is calculated from S/E/C suffixes by the project rule:
S + E + C <= 6 -> QM, 7 -> A, 8 -> B, 9 -> C, >= 10 -> D.
"""
from __future__ import annotations

import re
from typing import Any

ASIL_ORDER = {"QM": 0, "A": 1, "B": 2, "C": 3, "D": 4}
ASIL_BY_SCORE = {7: "A", 8: "B", 9: "C"}


def normalize_sec(value: Any, prefix: str) -> str | None:
    """Extract S/E/C level from strings such as 'S3', '3', or 'E2: ...'."""
    if value is None:
        return None
    text = str(value).strip().upper().replace("：", ":")
    prefix = prefix.upper()
    match = re.search(rf"\b{prefix}\s*([0-4])\b", text)
    if match:
        return f"{prefix}{match.group(1)}"
    match = re.fullmatch(r"[0-4]", text)
    if match:
        return f"{prefix}{text}"
    match = re.match(r"^([0-4])(?:\D|$)", text)
    if match:
        return f"{prefix}{match.group(1)}"
    return None


def sec_suffix(value: Any, prefix: str) -> int | None:
    level = normalize_sec(value, prefix)
    if not level:
        return None
    return int(level[1:])


def asil_from_score(score: int) -> str:
    if score <= 6:
        return "QM"
    if score >= 10:
        return "D"
    return ASIL_BY_SCORE[score]


def asil_from_sec(severity: Any, exposure: Any, controllability: Any) -> str | None:
    s = sec_suffix(severity, "S")
    e = sec_suffix(exposure, "E")
    c = sec_suffix(controllability, "C")
    if s is None or e is None or c is None:
        return None
    return asil_from_score(s + e + c)


def normalize_asil(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"[\s\u3000]+", "", str(value).upper())
    if text in {"", "NAN", "NONE", "NULL"}:
        return None
    if text in ASIL_ORDER:
        return text
    match = re.search(r"ASIL\W*([ABCD])", text)
    if match:
        return match.group(1)
    if "QM" in text:
        return "QM"
    match = re.search(r"\b([ABCD])\b", text)
    if match:
        return match.group(1)
    return None


def max_asil(values: list[Any]) -> str | None:
    best = None
    best_score = -1
    for value in values:
        asil = normalize_asil(value)
        if asil is not None and ASIL_ORDER[asil] > best_score:
            best = asil
            best_score = ASIL_ORDER[asil]
    return best


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("severity")
    parser.add_argument("exposure")
    parser.add_argument("controllability")
    args = parser.parse_args()
    print(asil_from_sec(args.severity, args.exposure, args.controllability) or "nan")
