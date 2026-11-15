"""
ConsumerShield — Document Parser
Parses PDFs (via Docling or PyMuPDF fallback), plain text files,
and WhatsApp-style chat exports into a uniform dict structure.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List


_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}
_CHAT_KEYWORDS = {"whatsapp", "chat"}

def detect_file_type(filepath: str) -> str:
    """Return one of 'pdf', 'image', 'text', 'chat_export' based on extension / naming heuristics."""
    ext = os.path.splitext(filepath)[1].lower()
    basename = os.path.basename(filepath).lower()

    if ext == ".pdf":
        return "pdf"
    if ext in _IMAGE_EXTS:
        return "image"
    if ext == ".txt" and any(kw in basename for kw in _CHAT_KEYWORDS):
        return "chat_export"
    return "text"


def _parse_pdf_docling(filepath: str) -> Dict[str, Any]:
    """Parse a PDF using the Docling library for layout-aware extraction."""
    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    result = converter.convert(filepath)
    full_text = result.document.export_to_markdown()

    pages: List[Dict[str, Any]] = []
    pages.append({"page_num": 1, "text": full_text, "tables": []})

    return {"text": full_text, "pages": pages, "method": "docling"}


def _parse_pdf_pymupdf(filepath: str) -> Dict[str, Any]:
    """Fallback PDF parser using PyMuPDF (fitz)."""
    import fitz

    doc = fitz.open(filepath)
    pages: List[Dict[str, Any]] = []
    all_text_parts: List[str] = []

    for page_num, page in enumerate(doc, start=1):
        page_text = page.get_text("text")
        all_text_parts.append(page_text)

        tables: List[List[List[str]]] = []
        try:
            tab_finder = page.find_tables()
            for table in tab_finder.tables:
                tables.append(table.extract())
        except Exception:
            pass

        pages.append({"page_num": page_num, "text": page_text, "tables": tables})

    doc.close()
    return {"text": "\n".join(all_text_parts), "pages": pages, "method": "pymupdf"}


def parse_pdf(filepath: str) -> Dict[str, Any]:
    """Parse a PDF document. Tries PyMuPDF (fast & local) first, falls back to Docling."""
    try:
        return _parse_pdf_pymupdf(filepath)
    except Exception:
        pass

    try:
        return _parse_pdf_docling(filepath)
    except Exception as exc:
        raise RuntimeError(f"Failed to parse PDF '{filepath}': {exc}") from exc


def parse_text_file(filepath: str) -> Dict[str, Any]:
    """Read a plain text file (email dump, notes, etc.) into the standard structure."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except Exception as exc:
        raise RuntimeError(f"Failed to read text file '{filepath}': {exc}") from exc

    return {
        "text": text,
        "pages": [{"page_num": 1, "text": text, "tables": []}],
        "method": "text",
    }


_CHAT_LINE_RE = re.compile(
    r"^"
    r"(?:\[?"
    r"(\d{1,2}/\d{1,2}/\d{2,4})"
    r"[,\s]+"
    r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s?[APap][Mm])?)"
    r"\]?"
    r"[\s\-–]+)"
    r"(.+?):\s"
    r"(.*)",
    re.DOTALL,
)


def parse_chat_export(filepath: str) -> Dict[str, Any]:
    """Parse a WhatsApp-style chat export into structured messages."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            raw_text = fh.read()
    except Exception as exc:
        raise RuntimeError(f"Failed to read chat export '{filepath}': {exc}") from exc

    messages: List[Dict[str, str]] = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = _CHAT_LINE_RE.match(line)
        if match:
            date_str, time_str, sender, body = match.groups()
            messages.append({
                "date": date_str.strip(),
                "time": time_str.strip(),
                "sender": sender.strip(),
                "message": body.strip(),
            })
        elif messages:
            messages[-1]["message"] += "\n" + line

    return {
        "text": raw_text,
        "pages": [{"page_num": 1, "text": raw_text, "tables": []}],
        "messages": messages,
        "method": "chat_export",
    }


def parse_document(filepath: str) -> Dict[str, Any]:
    """Detect the file type and delegate to the appropriate parser.

    Returns the standard dict with keys: text, pages, method (and messages for chat exports).
    """
    ftype = detect_file_type(filepath)

    if ftype == "pdf":
        return parse_pdf(filepath)
    if ftype == "image":
        return {
            "text": "",
            "pages": [],
            "method": "image",
            "note": "Use vision_parser.analyze_product_image() for image analysis.",
        }
    if ftype == "chat_export":
        return parse_chat_export(filepath)

    return parse_text_file(filepath)
