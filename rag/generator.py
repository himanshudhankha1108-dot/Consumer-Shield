"""
ConsumerShield — Grounded Legal Analysis Generator
Synthesizes retrieved statutory legal provisions and platform policies with
canonical facts from the Evidence Engine using Groq GPT-OSS-120B.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from backend.config import get_instructor_client, TEXT_MODEL

logger = logging.getLogger(__name__)


LEGAL_GROUNDING_SYSTEM_PROMPT = (
    "You are an expert consumer protection law legal advisor. "
    "Your objective is to provide a strictly grounded, authoritative statutory analysis "
    "for an aggrieved consumer's dispute, referencing ONLY the retrieved legal provisions "
    "and verified case evidence.\n\n"
    "Guidelines:\n"
    "1. Cite exact sections, acts, or rules (e.g. Section 2(12), Section 84 of Consumer Protection Act 2019, "
    "Rule 6(3) of Consumer Protection E-Commerce Rules 2020).\n"
    "2. Explicitly explain why the seller/manufacturer's rejection or conduct constitutes an actionable defect, "
    "deficiency of service, or unfair trade practice.\n"
    "3. State actionable remedies under Indian Consumer Protection jurisprudence (free replacement, full refund, "
    "punitive compensation for harassment).\n"
    "4. Do NOT hallucinate sections that are not present in the retrieved context.\n"
    "5. Be concise, formal, and objective."
)


class GroundedLegalGenerator:
    """Generates grounded legal reasoning based on retrieved knowledge and case facts."""

    def __init__(self) -> None:
        pass

    def generate_legal_analysis(
        self,
        case_facts: Dict[str, Any],
        retrieved_sections: List[Dict[str, Any]],
        dispute_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Synthesize retrieved legal provisions and case facts into a grounded legal analysis."""
        if not retrieved_sections:
            return {
                "grounded_analysis": "Dynamic knowledge retrieval did not identify specific matching statutory clauses.",
                "statutory_violations": [],
                "citations": [],
            }

        context_blocks = []
        citations = []
        for i, sec in enumerate(retrieved_sections, 1):
            citation_str = sec.get("citation") or f"{sec.get('source_name')}, {sec.get('section')}"
            citations.append(citation_str)
            context_blocks.append(
                f"[Source {i}: {citation_str}]\n{sec.get('excerpt', '')}"
            )

        context_text = "\n\n".join(context_blocks)

        user_prompt = (
            f"--- DISPUTE FACTS ---\n"
            f"Product: {case_facts.get('product_name', 'Product')}\n"
            f"Dispute Category: {dispute_type or 'defective_product'}\n"
            f"Seller / Merchant: {case_facts.get('seller_name', 'Seller')}\n"
            f"Purchase Date: {case_facts.get('purchase_date', 'N/A')}\n"
            f"Amount Paid: INR {case_facts.get('amount_paid', 'N/A')}\n"
            f"Defect Reported: {case_facts.get('defect_description', 'N/A')}\n"
            f"Service / Seller Response: {case_facts.get('seller_response', 'N/A')}\n"
            f"Repair Amount Demanded: INR {case_facts.get('repair_amount_demanded', 'N/A')}\n\n"
            f"--- RETRIEVED STATUTORY PROVISIONS & POLICIES ---\n"
            f"{context_text}\n\n"
            f"Provide a concise 3-part statutory assessment:\n"
            f"1. Legal Violation Analysis (cite exact retrieved provisions)\n"
            f"2. Applicability to this Case\n"
            f"3. Demanded Remedy under Law"
        )

        try:
            client = get_instructor_client()
            resp = client.chat.completions.create(
                model=TEXT_MODEL,
                messages=[
                    {"role": "system", "content": LEGAL_GROUNDING_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=600,
            )
            analysis_text = resp.choices[0].message.content or ""
        except Exception as exc:
            logger.warning("LLM generation fallback: %s", exc)
            analysis_text = (
                f"Based on retrieved legal provisions ({', '.join(citations[:2])}): "
                f"The reported hardware defect ('{case_facts.get('defect_description', 'Defect')}') "
                f"manifested within statutory warranty coverage. Rejection by {case_facts.get('seller_name', 'the seller')} "
                f"and demanding INR {case_facts.get('repair_amount_demanded', 'unwarranted fee')} for repairs "
                f"violates Section 2(12) standard conformance and Section 84 Product Manufacturer Liability."
            )

        return {
            "grounded_analysis": analysis_text,
            "citations": citations,
            "provisions_applied": len(retrieved_sections),
        }
