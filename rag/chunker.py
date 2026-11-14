"""
ConsumerShield — Hierarchical Parent-Child Legal Document Chunker
Preserves legal sections, subsection numbers, provisos, and explanations.
Generates full-context parent chunks and dense-searchable child chunks.
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional


class HierarchicalChunker:
    """Splits legal and policy markdown documents into hierarchical parent-child chunks.

    Parent chunks retain the complete legal section or policy clause to ensure
    statutory integrity. Child chunks are smaller passages tailored for semantic
    and keyword retrieval, while retaining a direct pointer to the parent context.
    """

    def __init__(
        self,
        max_child_size: int = 450,
        child_overlap: int = 60,
        min_chunk_size: int = 40,
    ) -> None:
        self.max_child_size = max_child_size
        self.child_overlap = child_overlap
        self.min_chunk_size = min_chunk_size

    # ── Section Heading Regex Patterns ─────────────────────────
    # Matches markdown headers e.g. ### Section 2(12) — "Defect", ## Rule 6: Duties...
    _SECTION_HEADER_RE = re.compile(
        r"(?m)^(#{2,4}\s+(?:Section|Rule|Chapter|\d+\.|\bArticle\b)[^\n]+)",
        re.IGNORECASE,
    )

    _SECTION_NUMBER_RE = re.compile(
        r"(Section\s+\d+(?:\(\d+\))*(?:\([a-zivx]+\))*|Rule\s+\d+(?:\(\d+\))*|Article\s+\d+)",
        re.IGNORECASE,
    )

    _SUBSECTION_SPLIT_RE = re.compile(
        r"(?m)(?=^\s*(?:\(\d+\)|\([a-z]\)|\([ivx]+\)|Provided that|Explanation:|\d+\.\s))"
    )

    def _slugify(self, text: str) -> str:
        s = re.sub(r"[^\w\s-]", "", text).strip().lower()
        return re.sub(r"[-\s]+", "_", s)[:40]

    def chunk_legal_document(
        self, body: str, metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Parse a statutory legal document into hierarchical parent-child chunks."""
        return self._chunk_document(body, metadata, default_type="legal")

    def chunk_policy_document(
        self, body: str, metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Parse a platform policy or warranty guideline into hierarchical chunks."""
        return self._chunk_document(body, metadata, default_type="policy")

    def _chunk_document(
        self,
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
        default_type: str = "legal",
    ) -> List[Dict[str, Any]]:
        metadata = dict(metadata or {})
        doc_title = metadata.get("source_name") or metadata.get("title") or "Legal Document"
        doc_id = self._slugify(doc_title)
        metadata.setdefault("document_id", doc_id)
        metadata.setdefault("document_title", doc_title)
        metadata.setdefault("document_type", default_type)
        metadata.setdefault("jurisdiction", metadata.get("jurisdiction", "India"))
        metadata.setdefault("source_authority", metadata.get("issuing_authority") or metadata.get("act_number") or doc_title)

        # Split text into sections using markdown headings
        sections = self._split_into_sections(body)
        if not sections:
            # Fallback for plain unsectioned text
            sections = [("General Provisions", body.strip())]

        all_chunks: List[Dict[str, Any]] = []

        for p_idx, (sec_header, sec_text) in enumerate(sections, start=1):
            if len(sec_text.strip()) < self.min_chunk_size:
                continue

            sec_num_match = self._SECTION_NUMBER_RE.search(sec_header)
            section_number = sec_num_match.group(1) if sec_num_match else None

            parent_id = f"{doc_id}_p{p_idx}"
            if section_number:
                clean_sec = re.sub(r"[^\w]", "_", section_number.lower()).strip("_")
                parent_id = f"{doc_id}_{clean_sec}"

            parent_metadata = {
                **metadata,
                "parent_id": parent_id,
                "section_heading": sec_header,
                "section_number": section_number,
                "chunk_type": "parent",
            }

            parent_chunk = {
                "chunk_id": parent_id,
                "parent_id": parent_id,
                "text": f"{sec_header}\n\n{sec_text}".strip(),
                "parent_text": f"{sec_header}\n\n{sec_text}".strip(),
                "metadata": parent_metadata,
            }
            all_chunks.append(parent_chunk)

            # Generate child chunks for the parent
            child_chunks = self._generate_children(
                parent_id=parent_id,
                section_header=sec_header,
                section_number=section_number,
                section_body=sec_text,
                base_metadata=metadata,
                parent_text=parent_chunk["text"],
            )
            all_chunks.extend(child_chunks)

        return all_chunks

    def _split_into_sections(self, body: str) -> List[tuple[str, str]]:
        """Split markdown text into (heading, content) tuples."""
        matches = list(self._SECTION_HEADER_RE.finditer(body))
        if not matches:
            # Try splitting by double newline or h2 if h3 not found
            h2_matches = list(re.finditer(r"(?m)^(#{1,3}\s+[^\n]+)", body))
            if h2_matches:
                matches = h2_matches

        if not matches:
            return []

        sections: List[tuple[str, str]] = []
        for i, m in enumerate(matches):
            header = m.group(1).lstrip("#").strip()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            content = body[start:end].strip()
            sections.append((header, content))

        return sections

    def _generate_children(
        self,
        parent_id: str,
        section_header: str,
        section_number: Optional[str],
        section_body: str,
        base_metadata: Dict[str, Any],
        parent_text: str,
    ) -> List[Dict[str, Any]]:
        """Decompose parent text into child chunks along clauses or subsections."""
        subsections = self._SUBSECTION_SPLIT_RE.split(section_body)
        subsections = [s.strip() for s in subsections if s.strip()]

        raw_passages: List[str] = []

        if len(subsections) > 1:
            for sub in subsections:
                if len(sub) > self.max_child_size:
                    # Further split large subsections with sliding window
                    raw_passages.extend(self._sliding_window(sub))
                elif len(sub) >= self.min_chunk_size:
                    raw_passages.append(sub)
        else:
            if len(section_body) <= self.max_child_size:
                raw_passages = [section_body]
            else:
                raw_passages = self._sliding_window(section_body)

        children: List[Dict[str, Any]] = []
        for c_idx, raw in enumerate(raw_passages, start=1):
            child_id = f"{parent_id}_c{c_idx}"
            
            # Detect subsection if present (e.g. (1), (a), (iv))
            sub_match = re.search(r"^\s*(\(\d+\)|\([a-z]\)|\([ivx]+\)|\d+\.)", raw)
            sub_number = sub_match.group(1) if sub_match else None

            # Prepend section context for rich semantic retrieval
            contextualized_text = f"[{section_header}] {raw}"

            child_metadata = {
                **base_metadata,
                "parent_id": parent_id,
                "child_id": child_id,
                "section_heading": section_header,
                "section_number": section_number,
                "subsection_number": sub_number,
                "chunk_type": "child",
            }

            children.append(
                {
                    "chunk_id": child_id,
                    "parent_id": parent_id,
                    "text": contextualized_text,
                    "raw_text": raw,
                    "parent_text": parent_text,
                    "metadata": child_metadata,
                }
            )

        return children

    def _sliding_window(self, text: str) -> List[str]:
        """Split long passage into overlapping windows at sentence boundaries."""
        sentences = re.split(r"(?<=[.!?;\n])\s+", text)
        chunks: List[str] = []
        curr_words: List[str] = []
        curr_len = 0

        for sent in sentences:
            sent_len = len(sent)
            if curr_len + sent_len > self.max_child_size and curr_words:
                chunks.append(" ".join(curr_words))
                # Retain overlap words
                overlap_words = curr_words[-3:] if len(curr_words) >= 3 else curr_words
                curr_words = list(overlap_words)
                curr_len = sum(len(w) for w in curr_words) + len(curr_words)

            curr_words.append(sent)
            curr_len += sent_len + 1

        if curr_words:
            chunks.append(" ".join(curr_words))

        return [c for c in chunks if len(c) >= self.min_chunk_size]
