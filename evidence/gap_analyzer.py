"""
ConsumerShield — Evidence Gap Analysis Engine

Evaluates submitted documents against dispute-specific evidence
requirements and produces a completeness checklist with a weighted score.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from evidence.schemas import (
    DisputeType,
    DocumentType,
    EvidenceChecklistItem,
    ScoreDimension,
)

# ────────────────── Evidence requirement definitions ──────────────────
# Each entry: {"name": <human label>, "required": bool,
#              "doc_types": [DocumentType, ...] that satisfy this item,
#              "fact_keys": [str, ...] that partially satisfy this item}

_RequirementDef = Dict[str, Any]

_DEFECTIVE_PRODUCT_REQS: List[_RequirementDef] = [
    {
        "name": "Invoice/Receipt",
        "required": True,
        "doc_types": [DocumentType.INVOICE],
        "fact_keys": ["purchase_date", "amount_paid", "order_id"],
    },
    {
        "name": "Warranty Document",
        "required": True,
        "doc_types": [DocumentType.WARRANTY_CARD],
        "fact_keys": ["warranty_period_months", "warranty_type"],
    },
    {
        "name": "Product Defect Photo/Video",
        "required": True,
        "doc_types": [DocumentType.DEFECT_PHOTO],
        "fact_keys": ["defect_description"],
    },
    {
        "name": "Written Complaint to Seller",
        "required": True,
        "doc_types": [DocumentType.EMAIL, DocumentType.WHATSAPP],
        "fact_keys": ["complaint_date"],
    },
    {
        "name": "Seller Response/Denial",
        "required": False,
        "doc_types": [DocumentType.EMAIL, DocumentType.WHATSAPP],
        "fact_keys": ["seller_response", "seller_response_date"],
    },
    {
        "name": "Service Inspection Report",
        "required": False,
        "doc_types": [DocumentType.JOB_SHEET],
        "fact_keys": [],
    },
]

_DENIED_REFUND_REQS: List[_RequirementDef] = [
    {
        "name": "Invoice/Receipt",
        "required": True,
        "doc_types": [DocumentType.INVOICE],
        "fact_keys": ["purchase_date", "amount_paid", "order_id"],
    },
    {
        "name": "Return Request Record",
        "required": True,
        "doc_types": [DocumentType.EMAIL, DocumentType.WHATSAPP],
        "fact_keys": [],
    },
    {
        "name": "Seller Denial Communication",
        "required": True,
        "doc_types": [DocumentType.EMAIL, DocumentType.WHATSAPP],
        "fact_keys": ["seller_response"],
    },
    {
        "name": "Platform Escalation Record",
        "required": False,
        "doc_types": [DocumentType.EMAIL],
        "fact_keys": [],
    },
    {
        "name": "Product Photos",
        "required": False,
        "doc_types": [DocumentType.DEFECT_PHOTO],
        "fact_keys": [],
    },
]

_WARRANTY_REJECTION_REQS: List[_RequirementDef] = [
    {
        "name": "Invoice",
        "required": True,
        "doc_types": [DocumentType.INVOICE],
        "fact_keys": ["purchase_date", "amount_paid"],
    },
    {
        "name": "Warranty Card",
        "required": True,
        "doc_types": [DocumentType.WARRANTY_CARD],
        "fact_keys": ["warranty_period_months"],
    },
    {
        "name": "Defect Evidence",
        "required": True,
        "doc_types": [DocumentType.DEFECT_PHOTO],
        "fact_keys": ["defect_description"],
    },
    {
        "name": "Service Center Job Sheet",
        "required": True,
        "doc_types": [DocumentType.JOB_SHEET],
        "fact_keys": [],
    },
    {
        "name": "Written Rejection from Brand",
        "required": True,
        "doc_types": [DocumentType.EMAIL, DocumentType.WHATSAPP],
        "fact_keys": ["seller_response"],
    },
]

_NON_DELIVERY_REQS: List[_RequirementDef] = [
    {
        "name": "Order Confirmation",
        "required": True,
        "doc_types": [DocumentType.EMAIL, DocumentType.INVOICE],
        "fact_keys": ["order_id"],
    },
    {
        "name": "Payment Proof",
        "required": True,
        "doc_types": [DocumentType.INVOICE],
        "fact_keys": ["amount_paid"],
    },
    {
        "name": "Delivery Status/Tracking",
        "required": True,
        "doc_types": [DocumentType.EMAIL],
        "fact_keys": ["delivery_date"],
    },
    {
        "name": "Complaint to Seller",
        "required": True,
        "doc_types": [DocumentType.EMAIL, DocumentType.WHATSAPP],
        "fact_keys": ["complaint_date"],
    },
    {
        "name": "Platform Communication",
        "required": False,
        "doc_types": [DocumentType.EMAIL],
        "fact_keys": [],
    },
]

_DEFAULT_REQS: List[_RequirementDef] = [
    {
        "name": "Invoice/Receipt",
        "required": True,
        "doc_types": [DocumentType.INVOICE],
        "fact_keys": ["purchase_date", "amount_paid"],
    },
    {
        "name": "Supporting Communication",
        "required": True,
        "doc_types": [DocumentType.EMAIL, DocumentType.WHATSAPP],
        "fact_keys": ["complaint_date"],
    },
    {
        "name": "Evidence of Issue",
        "required": True,
        "doc_types": [DocumentType.DEFECT_PHOTO, DocumentType.JOB_SHEET],
        "fact_keys": ["defect_description"],
    },
    {
        "name": "Seller/Service Provider Response",
        "required": False,
        "doc_types": [DocumentType.EMAIL, DocumentType.WHATSAPP],
        "fact_keys": ["seller_response"],
    },
]

_EVIDENCE_REQUIREMENTS: Dict[DisputeType, List[_RequirementDef]] = {
    DisputeType.DEFECTIVE_PRODUCT: _DEFECTIVE_PRODUCT_REQS,
    DisputeType.DENIED_REFUND: _DENIED_REFUND_REQS,
    DisputeType.WARRANTY_REJECTION: _WARRANTY_REJECTION_REQS,
    DisputeType.NON_DELIVERY: _NON_DELIVERY_REQS,
}

# ────────────────── Scoring dimensions ──────────────────

_SCORE_DIMENSIONS: List[Dict[str, Any]] = [
    {"dimension": "Purchase Evidence", "max_score": 25, "item_keywords": ["invoice", "receipt", "order", "payment"]},
    {"dimension": "Warranty/Policy Evidence", "max_score": 20, "item_keywords": ["warranty", "return", "policy"]},
    {"dimension": "Defect Evidence", "max_score": 20, "item_keywords": ["defect", "photo", "video", "damage", "evidence of issue"]},
    {"dimension": "Communication History", "max_score": 20, "item_keywords": ["complaint", "response", "denial", "communication", "escalation", "rejection"]},
    {"dimension": "Timeline Completeness", "max_score": 15, "item_keywords": ["delivery", "tracking", "job sheet", "service", "inspection"]},
]


class EvidenceGapAnalyzer:
    """Evaluates uploaded documents against dispute-specific evidence
    requirements and produces a completeness checklist with a weighted
    score.

    Parameters
    ----------
    dispute_type:
        The type of consumer dispute being analysed.
    """

    def __init__(self, dispute_type: DisputeType) -> None:
        self.dispute_type = dispute_type
        self._requirements = _EVIDENCE_REQUIREMENTS.get(
            dispute_type, _DEFAULT_REQS
        )

    # ── Analysis ───────────────────────────────────────────────

    def analyze(
        self,
        uploaded_doc_types: List[DocumentType],
        resolved_facts: Optional[Dict[str, Any]] = None,
        facts: Optional[Dict[str, Any]] = None,
        uploaded_files: Optional[List[Dict[str, Any]]] = None,
    ) -> List[EvidenceChecklistItem]:
        if resolved_facts is None:
            resolved_facts = facts or {}
        uploaded_set = set(uploaded_doc_types)
        checklist: List[EvidenceChecklistItem] = []

        for req in self._requirements:
            name: str = req["name"]
            required: bool = req["required"]
            matching_doc_types: List[DocumentType] = req["doc_types"]
            fact_keys: List[str] = req.get("fact_keys", [])

            # Check whether any matching document type was uploaded.
            has_doc = bool(uploaded_set & set(matching_doc_types))

            # Match source filename if available
            source_file = None
            if uploaded_files:
                for uf in uploaded_files:
                    uf_name = uf.get("filename", "")
                    uf_dt = uf.get("doc_type")
                    if uf_dt in matching_doc_types or (isinstance(uf_dt, str) and uf_dt in [m.value for m in matching_doc_types]):
                        source_file = uf_name
                        has_doc = True
                        break
                    # Filename heuristic matching
                    lower_uf = uf_name.lower()
                    if any(m.value in lower_uf for m in matching_doc_types if len(m.value) > 3):
                        source_file = uf_name
                        has_doc = True
                        break

            # Check whether relevant facts were resolved.
            matched_facts = [
                k for k in fact_keys
                if k in resolved_facts and resolved_facts[k] is not None
            ]
            has_facts = len(matched_facts) > 0

            if has_doc:
                status = "found"
                notes = f"Verified via document {source_file or 'in ledger'}."
            elif has_facts:
                status = "partial"
                notes = (
                    f"No matching document uploaded, but related facts "
                    f"extracted: {', '.join(matched_facts)}."
                )
            else:
                status = "missing"
                notes = "Not found in uploaded documents."

            checklist.append(
                EvidenceChecklistItem(
                    item_name=name,
                    required=required,
                    status=status,
                    source_filename=source_file,
                    notes=notes,
                )
            )

        return checklist

    # ── Missing evidence ───────────────────────────────────────

    @staticmethod
    def get_missing_evidence(
        checklist: List[EvidenceChecklistItem],
    ) -> List[str]:
        """Return human-readable descriptions of missing evidence items.

        Only ``required`` items with status ``"missing"`` or ``"partial"``
        are included.
        """
        missing: List[str] = []
        for item in checklist:
            if item.status == "missing":
                label = "(Required)" if item.required else "(Recommended)"
                missing.append(f"{item.item_name} {label} — {item.notes}")
            elif item.status == "partial" and item.required:
                missing.append(
                    f"{item.item_name} (Required, Partial) — {item.notes}"
                )
        return missing

    # ── Scoring ────────────────────────────────────────────────

    @staticmethod
    def calculate_evidence_score(
        checklist: List[EvidenceChecklistItem],
    ) -> Tuple[int, List[ScoreDimension]]:
        """Compute a weighted evidence completeness score.

        The score is distributed across five dimensions:

        * **Purchase Evidence** (25 points)
        * **Warranty/Policy Evidence** (20 points)
        * **Defect Evidence** (20 points)
        * **Communication History** (20 points)
        * **Timeline Completeness** (15 points)

        Each checklist item is mapped to the dimension whose keywords best
        match the item name.  Within a dimension the score is split evenly
        across matched items: ``"found"`` ⇒ full share, ``"partial"`` ⇒
        half share, ``"missing"`` ⇒ 0.

        Returns
        -------
        Tuple[int, List[ScoreDimension]]
            ``(total_score, list_of_ScoreDimension)``
        """
        dimensions: List[ScoreDimension] = []
        total_score = 0

        for dim_def in _SCORE_DIMENSIONS:
            dim_name: str = dim_def["dimension"]
            max_score: int = dim_def["max_score"]
            keywords: List[str] = dim_def["item_keywords"]

            # Collect checklist items that match this dimension.
            matched_items: List[EvidenceChecklistItem] = []
            for item in checklist:
                item_lower = item.item_name.lower()
                if any(kw in item_lower for kw in keywords):
                    matched_items.append(item)

            if not matched_items:
                dimensions.append(
                    ScoreDimension(
                        dimension=dim_name,
                        max_score=max_score,
                        actual_score=0,
                        details="No matching evidence items.",
                    )
                )
                continue

            per_item = max_score / len(matched_items)
            earned = 0.0
            details_parts: List[str] = []

            for item in matched_items:
                if item.status == "found":
                    earned += per_item
                    details_parts.append(f"{item.item_name}: ✓ found")
                elif item.status == "partial":
                    earned += per_item * 0.5
                    details_parts.append(f"{item.item_name}: ~ partial")
                else:
                    details_parts.append(f"{item.item_name}: ✗ missing")

            actual = round(earned)
            total_score += actual
            dimensions.append(
                ScoreDimension(
                    dimension=dim_name,
                    max_score=max_score,
                    actual_score=actual,
                    details="; ".join(details_parts),
                )
            )

        return total_score, dimensions
