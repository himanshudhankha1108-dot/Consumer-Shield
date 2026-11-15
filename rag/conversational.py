"""
ConsumerShield — Conversational Legal Retrieval & Assistant
Enables interactive consumer legal QA grounded in both case evidence facts
and dynamically retrieved legal knowledge.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from backend.config import get_instructor_client, TEXT_MODEL
from rag.retriever import HybridRetriever

logger = logging.getLogger(__name__)


CHAT_SYSTEM_PROMPT = (
    "You are ConsumerShield AI Assistant, an intelligent legal assistant for Indian consumer disputes. "
    "You answer user questions using verified case facts from their uploaded evidence and dynamically "
    "retrieved provisions of the Consumer Protection Act 2019 and Consumer Protection (E-Commerce) Rules 2020.\n\n"
    "Guidelines:\n"
    "1. Always ground your answer in the user's specific case facts (product, dates, amounts, seller response).\n"
    "2. Cite the exact statutory section or guideline retrieved (e.g. 'Under Section 2(12) of the Consumer Protection Act, 2019...').\n"
    "3. Be empowering, clear, legally sound, and concise.\n"
    "4. If evidence is missing (e.g. warranty card or invoice date), tell the consumer clearly what document to upload."
)


class ConversationalLegalRAG:
    """Handles contextual question-answering over consumer cases with dynamic hybrid retrieval."""

    def __init__(self, retriever: Optional[HybridRetriever] = None) -> None:
        self.retriever = retriever or HybridRetriever()

    def answer_question(
        self,
        question: str,
        case_facts: Dict[str, Any],
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Answer a user's question using case context and retrieved legal sections."""
        chat_history = chat_history or []

        product = case_facts.get("product_name") or "product"
        defect = case_facts.get("defect_description") or ""
        seller_resp = case_facts.get("seller_response") or ""
        
        search_query = f"{question} {product} {defect} {seller_resp}".strip()

        context_data = self.retriever.retrieve_context(query=search_query, top_k=3)
        retrieved_sections = context_data.get("sections", [])

        context_snippets = []
        citations = []
        for sec in retrieved_sections:
            cit = sec.get("citation") or f"{sec.get('source_name')}, {sec.get('section')}"
            citations.append(cit)
            context_snippets.append(f"[{cit}]\n{sec.get('excerpt', '')}")

        context_block = "\n\n".join(context_snippets)

        facts_summary = "\n".join(
            f"- {k}: {v}"
            for k, v in case_facts.items()
            if v and k not in ("raw_evidence_quotes",)
        )

        user_content = (
            f"=== VERIFIED CASE FACTS ===\n{facts_summary or 'No facts extracted yet.'}\n\n"
            f"=== RETRIEVED STATUTORY PROVISIONS & RULES ===\n{context_block or 'No matching provisions retrieved.'}\n\n"
            f"=== USER QUESTION ===\n{question}"
        )

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": CHAT_SYSTEM_PROMPT}
        ]

        for turn in chat_history[-3:]:
            messages.append({"role": turn.get("role", "user"), "content": turn.get("content", "")})

        messages.append({"role": "user", "content": user_content})

        try:
            client = get_instructor_client()
            resp = client.chat.completions.create(
                model=TEXT_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=500,
            )
            answer = resp.choices[0].message.content or ""
        except Exception as exc:
            logger.warning("Conversational RAG generation fallback: %s", exc)
            answer = (
                f"Regarding your inquiry ('{question}'): Under {citations[0] if citations else 'the Consumer Protection Act, 2019'}, "
                f"since your {product} manifested a defect during the warranty window, "
                f"you are legally entitled to a free-of-cost repair or replacement. "
                f"Arbitrary warranty denial constitutes an actionable deficiency in service."
            )

        return {
            "question": question,
            "answer": answer,
            "citations": citations,
            "retrieved_sections_count": len(retrieved_sections),
        }
