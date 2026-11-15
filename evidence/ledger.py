"""
ConsumerShield — Canonical Fact Ledger & Conflict Detector

Maintains a per-field list of extracted facts from multiple documents,
automatically detects conflicts (different values) and corroborations
(matching values), and supports manual conflict resolution.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from dateutil import parser as date_parser

from evidence.schemas import (
    ConflictAlert,
    DocumentType,
    FactItem,
    VerificationStatus,
)

_SOURCE_PRIORITY: List[DocumentType] = [
    DocumentType.INVOICE,
    DocumentType.WARRANTY_CARD,
    DocumentType.JOB_SHEET,
    DocumentType.EMAIL,
    DocumentType.WHATSAPP,
    DocumentType.DEFECT_PHOTO,
    DocumentType.USER_STATEMENT,
    DocumentType.OTHER,
]


def _normalize_str(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r'[\s\-_/]+', ' ', s)
    return s


_EMBEDDING_MODEL = None
_EMBEDDING_CACHE: Dict[str, Any] = {}


def _get_embedding_model():
    """Lazy-load BGE embedding model for zero-shot semantic matching."""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            _EMBEDDING_MODEL = SentenceTransformer("BAAI/bge-small-en-v1.5")
        except Exception:
            _EMBEDDING_MODEL = False
    return _EMBEDDING_MODEL


def _get_embedding(text: str):
    text_clean = text.strip().lower()
    if text_clean not in _EMBEDDING_CACHE:
        model = _get_embedding_model()
        if model:
            _EMBEDDING_CACHE[text_clean] = model.encode(text_clean, normalize_embeddings=True)
        else:
            return None
    return _EMBEDDING_CACHE[text_clean]


def _semantic_similarity(text1: str, text2: str) -> float:
    """Compute cosine similarity between two text snippets using BGE embeddings."""
    try:
        e1 = _get_embedding(text1)
        e2 = _get_embedding(text2)
        if e1 is not None and e2 is not None:
            from sentence_transformers import util
            return float(util.cos_sim(e1, e2)[0][0])
    except Exception:
        pass
    return 0.0


def _values_agree(val1: Any, val2: Any, field_name: str = "") -> bool:
    """Multi-tier agreement verification across extracted facts.

    Follows the 5-tier architecture:
    1. Basic Normalization & Exact Match (0ms)
    2. Date & Numeric Proximity
    3. Attribute & Token Overlap (Brand, model codes, prefixes)
    4. BGE Semantic Cosine Similarity (Zero-shot across any unseen product/category)
    5. Fallback: Creates ConflictAlert for Human Review in UI
    """
    if val1 == val2:
        return True

    try:
        f1, f2 = float(val1), float(val2)
        if abs(f1 - f2) < 0.01:
            return True
    except (ValueError, TypeError):
        pass

    s1, s2 = str(val1).strip(), str(val2).strip()
    n1, n2 = _normalize_str(s1), _normalize_str(s2)

    if n1 == n2:
        return True

    tokens1 = set(re.findall(r'[a-z0-9]+', n1))
    tokens2 = set(re.findall(r'[a-z0-9]+', n2))

    if "date" in field_name:
        try:
            d1 = date_parser.parse(s1, fuzzy=True).date()
            d2 = date_parser.parse(s2, fuzzy=True).date()
            if d1 == d2:
                return True
            if field_name == "defect_date" and abs((d1 - d2).days) <= 7:
                return True
        except Exception:
            pass

    if field_name == "model_number":
        if n1.startswith(n2) or n2.startswith(n1):
            return True
        shared_model_code = {t for t in tokens1 & tokens2 if any(c.isdigit() for c in t) and len(t) >= 2}
        if shared_model_code:
            return True

    if field_name in ["product_name", "product_category", "brand", "service_center", "seller_name", "warranty_type"]:
        if n1 in n2 or n2 in n1:
            return True
        if tokens1 and tokens2 and (tokens1.issubset(tokens2) or tokens2.issubset(tokens1)):
            return True
        if "authorized service provider" in n1 or "authorized service provider" in n2:
            return True
        sim = _semantic_similarity(s1, s2)
        if sim >= 0.78:
            return True

    if field_name in ["defect_description", "resolution_offered"]:
        kw = ["display", "screen", "motherboard", "power", "charging", "battery", "audio", "sound", "shut down", "black", "leak", "panel"]
        if {k for k in kw if k in n1} & {k for k in kw if k in n2}:
            return True
        if _semantic_similarity(s1, s2) >= 0.65:
            return True

    return False


def _source_rank(doc_type: DocumentType) -> int:
    """Return the priority rank for *doc_type* (lower is better).

    Sources not listed in the priority hierarchy receive the worst rank.
    """
    try:
        return _SOURCE_PRIORITY.index(doc_type)
    except ValueError:
        return len(_SOURCE_PRIORITY)


class CanonicalFactLedger:
    """Stores extracted facts keyed by field name and detects conflicts.

    Each field may accumulate multiple ``FactItem`` entries originating from
    different documents.  After every new recording the ledger re-evaluates
    whether the entries agree (→ ``VERIFIED``) or disagree (→
    ``CONFLICTING``).
    """

    def __init__(self) -> None:
        self._facts: Dict[str, List[FactItem]] = {}
        self._conflicts: Dict[str, ConflictAlert] = {}
        self._resolutions: Dict[str, Any] = {}

    @property
    def raw_facts(self) -> Dict[str, List[FactItem]]:
        """Return the dictionary of raw FactItems keyed by field name."""
        return self._facts

    @property
    def conflicts(self) -> List[ConflictAlert]:
        """Return list of active ConflictAlert objects."""
        return list(self._conflicts.values())

    @property
    def resolved_facts(self) -> Dict[str, Any]:
        """Return dictionary of resolved field values."""
        return {f: self.get_resolved_value(f) for f in self._facts}

    @property
    def canonical_records(self) -> List[Dict[str, Any]]:
        """Return a structured list of canonical facts (one per unique field)."""
        records: List[Dict[str, Any]] = []
        for field_name, entries in self._facts.items():
            if not entries:
                continue
            resolved_val = self.get_resolved_value(field_name)
            sources = list(dict.fromkeys(e.source_filename for e in entries if e.source_filename))
            is_conflicting = field_name in self._conflicts
            if is_conflicting:
                status = "conflicting"
            elif any(e.verification_status == VerificationStatus.USER_CONFIRMED for e in entries):
                status = "verified"
            elif len(entries) >= 2 or any(e.verification_status == VerificationStatus.VERIFIED for e in entries):
                status = "verified"
            else:
                status = entries[0].verification_status.value

            max_conf = max(e.confidence for e in entries)
            records.append({
                "field": field_name,
                "value": str(resolved_val) if resolved_val is not None else "",
                "sources": sources,
                "sources_count": len(sources),
                "confidence": max_conf,
                "status": status,
                "raw_values": list(dict.fromkeys(str(e.value) for e in entries)),
            })
        return records


    def record_fact(self, fact: FactItem) -> None:
        """Append *fact* and re-evaluate conflicts for its field."""
        self._facts.setdefault(fact.field_name, []).append(fact)
        self._evaluate_conflicts(fact.field_name)


    def _evaluate_conflicts(self, field_name: str) -> None:
        """Evaluate facts for *field_name* and update statuses.

        * If only one fact exists it stays ``EXTRACTED``.
        * If all values match they are promoted to ``VERIFIED`` with a small
          confidence boost (capped at 1.0).
        * If values differ a ``ConflictAlert`` is created, every entry is
          marked ``CONFLICTING``, and the highest-priority source is stored
          as the auto-resolved value.
        """
        entries = self._facts.get(field_name, [])
        if len(entries) < 2:
            return

        primary_entry = min(entries, key=lambda e: (_source_rank(e.source_doc_type), -len(str(e.value))))
        primary_val = primary_entry.value
        all_agree = all(_values_agree(primary_val, e.value, field_name) for e in entries)

        if all_agree:
            for e in entries:
                e.verification_status = VerificationStatus.VERIFIED
                e.confidence = min(e.confidence + 0.05, 1.0)
            self._conflicts.pop(field_name, None)

            if field_name == "defect_date":
                try:
                    best = min(entries, key=lambda e: date_parser.parse(str(e.value), fuzzy=True).date())
                except Exception:
                    best = min(entries, key=lambda e: (_source_rank(e.source_doc_type), -len(str(e.value))))
            elif field_name == "seller_response":
                rejections = [e for e in entries if any(w in str(e.value).lower() for w in ["reject", "denied", "refus", "no refund", "payment", "exclude"])]
                if rejections:
                    best = min(rejections, key=lambda e: (_source_rank(e.source_doc_type), -len(str(e.value))))
                else:
                    best = min(entries, key=lambda e: (_source_rank(e.source_doc_type), -len(str(e.value))))
            else:
                best = min(entries, key=lambda e: (_source_rank(e.source_doc_type), -len(str(e.value))))
            self._resolutions[field_name] = best.value
        else:
            for e in entries:
                e.verification_status = VerificationStatus.CONFLICTING

            alert = ConflictAlert(
                field=field_name,
                values=[
                    {
                        "value": e.value,
                        "source": e.source_doc_type.value,
                        "file": e.source_filename,
                        "confidence": e.confidence,
                    }
                    for e in entries
                ],
                alert=(
                    f"Conflicting values detected for '{field_name}' across "
                    f"{len(entries)} sources."
                ),
            )
            self._conflicts[field_name] = alert

            if field_name not in self._resolutions:
                best = min(entries, key=lambda e: _source_rank(e.source_doc_type))
                self._resolutions[field_name] = best.value


    def resolve_conflict(
        self,
        field_name: str,
        chosen_value: Any,
        user_confirmed: bool = True,
    ) -> bool:
        """Manually resolve a conflict for *field_name*.

        All facts for the field are updated to ``USER_CONFIRMED`` and the
        chosen value is stored as the definitive resolution.
        """
        self._resolutions[field_name] = chosen_value
        self._conflicts.pop(field_name, None)
        if user_confirmed:
            for e in self._facts.get(field_name, []):
                e.verification_status = VerificationStatus.USER_CONFIRMED
        return True


    def get_resolved_value(self, field_name: str) -> Optional[Any]:
        """Return the resolved value for *field_name*, or ``None``."""
        if field_name in self._resolutions:
            return self._resolutions[field_name]
        entries = self._facts.get(field_name, [])
        if entries:
            best = min(entries, key=lambda e: _source_rank(e.source_doc_type))
            return best.value
        return None

    def get_summary(self) -> Dict[str, Any]:
        """Return a high-level summary of the ledger state.

        Returns a dict with:
        * ``resolved_facts`` — ``{field: resolved_value}``
        * ``conflicts`` — list of ``ConflictAlert`` dicts
        * ``total_raw_facts`` — total number of raw ``FactItem`` entries
        """
        resolved_facts: Dict[str, Any] = {}
        for field_name in self._facts:
            resolved_facts[field_name] = self.get_resolved_value(field_name)

        return {
            "resolved_facts": resolved_facts,
            "conflicts": [c.model_dump() for c in self._conflicts.values()],
            "total_raw_facts": sum(len(v) for v in self._facts.values()),
            "raw_facts_count": sum(len(v) for v in self._facts.values()),
        }


    def to_dict(self) -> Dict[str, Any]:
        """Serialise the entire ledger to a plain dict."""
        return {
            "facts": {
                field: [f.model_dump() for f in items]
                for field, items in self._facts.items()
            },
            "conflicts": {
                field: alert.model_dump()
                for field, alert in self._conflicts.items()
            },
            "resolutions": dict(self._resolutions),
        }
