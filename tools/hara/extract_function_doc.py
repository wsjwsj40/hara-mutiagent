#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract text, headings, and simple tables from function documents.

Supported inputs:
- .txt/.md/.markdown
- .docx via Python stdlib zipfile + XML parsing
- .doc via optional local antiword/catdoc command
- .pdf via optional local libraries (PyMuPDF, pypdf, pdfplumber) or pdftotext

The output is a normalized JSON document for Stage 0 function extraction.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import zipfile
from html import unescape
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


HEADING_RE = re.compile(r"^\s*(\d+(?:\.\d+)+)\s+(.+?)\s*$")
DOCX_NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
}


def clean_text(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"\s+", " ", text.replace("\u3000", " ")).strip()
    return text


def make_block(block_id: int, kind: str, text: str = "", **extra: Any) -> dict[str, Any]:
    text = clean_text(text)
    heading = HEADING_RE.match(text) if text else None
    block: dict[str, Any] = {
        "block_id": f"B{block_id:04d}",
        "type": kind,
        "section_id": heading.group(1) if heading else extra.pop("section_id", "nan"),
        "title": heading.group(2) if heading else extra.pop("title", "nan"),
        "text": text,
    }
    block.update(extra)
    return block


def paragraph_text(node: ET.Element) -> str:
    parts: list[str] = []
    for text_node in node.findall(".//w:t", DOCX_NS):
        if text_node.text:
            parts.append(text_node.text)
    return clean_text("".join(parts))


def table_rows(node: ET.Element) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in node.findall(".//w:tr", DOCX_NS):
        cells: list[str] = []
        for cell in row.findall("./w:tc", DOCX_NS):
            cell_parts = [paragraph_text(p) for p in cell.findall(".//w:p", DOCX_NS)]
            cells.append(clean_text(" ".join(part for part in cell_parts if part)))
        if any(cells):
            rows.append(cells)
    return rows


def extract_docx(path: Path) -> tuple[list[dict[str, Any]], str]:
    blocks: list[dict[str, Any]] = []
    with zipfile.ZipFile(path) as archive:
        xml_data = archive.read("word/document.xml")
    root = ET.fromstring(xml_data)
    body = root.find("w:body", DOCX_NS)
    if body is None:
        return blocks, "docx-xml-empty"

    block_id = 1
    for child in body:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            text = paragraph_text(child)
            if not text:
                continue
            kind = "heading" if HEADING_RE.match(text) else "paragraph"
            blocks.append(make_block(block_id, kind, text))
            block_id += 1
        elif tag == "tbl":
            rows = table_rows(child)
            if not rows:
                continue
            text = "\n".join("\t".join(row) for row in rows)
            blocks.append(make_block(block_id, "table", text, rows=rows))
            block_id += 1
    return blocks, "docx-xml"


def extract_text_blocks(path: Path) -> tuple[list[dict[str, Any]], str]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    blocks: list[dict[str, Any]] = []
    block_id = 1
    for raw in re.split(r"\n\s*\n", text):
        raw = clean_text(raw)
        if not raw:
            continue
        kind = "heading" if HEADING_RE.match(raw) else "paragraph"
        blocks.append(make_block(block_id, kind, raw))
        block_id += 1
    return blocks, "text"


def text_to_blocks(text: str, method: str) -> tuple[list[dict[str, Any]], str]:
    blocks: list[dict[str, Any]] = []
    block_id = 1
    for raw in re.split(r"\n\s*\n", text):
        raw = clean_text(raw)
        if not raw:
            continue
        kind = "heading" if HEADING_RE.match(raw) else "paragraph"
        blocks.append(make_block(block_id, kind, raw))
        block_id += 1
    return blocks, method


def extract_doc_binary(path: Path) -> tuple[list[dict[str, Any]], str]:
    commands = [
        ("antiword", ["antiword", str(path)]),
        ("catdoc", ["catdoc", str(path)]),
    ]
    for name, cmd in commands:
        try:
            proc = subprocess.run(
                cmd,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError:
            continue
        if proc.returncode == 0 and proc.stdout.strip():
            return text_to_blocks(proc.stdout, name)
    raise SystemExit("Unable to extract legacy .doc text. Convert it to .docx or install antiword/catdoc.")


def pdf_text_with_fitz(path: Path) -> str | None:
    try:
        import fitz  # type: ignore
    except Exception:
        return None
    doc = fitz.open(path)
    return "\n\n".join(page.get_text("text") for page in doc)


def pdf_text_with_pypdf(path: Path) -> str | None:
    try:
        import pypdf  # type: ignore
    except Exception:
        return None
    reader = pypdf.PdfReader(str(path))
    return "\n\n".join((page.extract_text() or "") for page in reader.pages)


def pdf_text_with_pdfplumber(path: Path) -> str | None:
    try:
        import pdfplumber  # type: ignore
    except Exception:
        return None
    with pdfplumber.open(path) as pdf:
        return "\n\n".join((page.extract_text() or "") for page in pdf.pages)


def pdf_text_with_pdftotext(path: Path) -> str | None:
    try:
        proc = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def extract_pdf(path: Path) -> tuple[list[dict[str, Any]], str]:
    methods = [
        ("pymupdf", pdf_text_with_fitz),
        ("pypdf", pdf_text_with_pypdf),
        ("pdfplumber", pdf_text_with_pdfplumber),
        ("pdftotext", pdf_text_with_pdftotext),
    ]
    text: str | None = None
    method_used = "pdf-unavailable"
    for name, extractor in methods:
        text = extractor(path)
        if text and text.strip():
            method_used = name
            break
    if not text or not text.strip():
        raise SystemExit("Unable to extract PDF text. Install PyMuPDF/pypdf/pdfplumber or pdftotext.")

    return text_to_blocks(text, method_used)


def extract(path: Path) -> tuple[list[dict[str, Any]], str]:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return extract_docx(path)
    if suffix == ".doc":
        return extract_doc_binary(path)
    if suffix == ".pdf":
        return extract_pdf(path)
    if suffix in {".txt", ".md", ".markdown"}:
        return extract_text_blocks(path)
    raise SystemExit(f"Unsupported input extension: {suffix}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Function document path")
    parser.add_argument("--out", required=True, help="Normalized JSON output path")
    args = parser.parse_args()

    input_path = Path(args.input)
    out_path = Path(args.out)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    blocks, method = extract(input_path)
    data = {
        "meta": {
            "source_path": str(input_path),
            "source_name": input_path.name,
            "source_type": input_path.suffix.lower().lstrip(".") or "text",
            "extraction_method": method,
            "blocks": len(blocks),
        },
        "blocks": blocks,
        "full_text": "\n\n".join(block.get("text", "") for block in blocks if block.get("text")),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(data["meta"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
