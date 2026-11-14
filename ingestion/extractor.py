"""
ConsumerShield — Structured Fact Extraction via Grok LLM
Extracts structured CaseExtractionOutput from document text,
then converts each non-null field into a FactItem for the Canonical Fact Ledger.
"""
from __future__ import annotations

import re
from typing import List

from evidence.schemas import (
    CaseExtractionOutput,
    DocumentType,
    FactItem,
    VerificationStatus,
)
from backend.config import get_instructor_client, TEXT_MODEL


# ────────────────── System Prompt ──────────────────

EXTRACTION_SYSTEM_PROMPT = (
    "You are a structured fact-extraction system for consumer disputes. "
    "Given a document, extract every factual field into the requested JSON schema.\n\n"
    "Rules:\n"
    "1. Extract all dates in ISO YYYY-MM-DD format.\n"
    "2. NEVER hallucinate — if a field is not present in the text, leave it null.\n"
    "3. In raw_evidence_quotes, include the exact verbatim snippets from the "
    "document that support each extracted value.\n"
    "4. Currency defaults to INR unless stated otherwise.\n"
    "5. CRITICAL: 'amount_paid' is ONLY the purchase price from an invoice. If a service center or email demands money for repairs/replacement, put that in 'repair_amount_demanded'.\n"
    "6. CRITICAL: 'seller_name' is ONLY the merchant/retailer who sold the product (e.g. Croma, Amazon, Flipkart). Put service/repair partners in 'service_center'.\n"
    "7. CRITICAL: 'seller_response' must capture the official response, denial, or warranty rejection stated by the seller or authorized service center (e.g. 'free warranty repair is REJECTED citing moisture/wear'). Whenever a document contains a warranty rejection or payment demand, you MUST extract 'seller_response' AND also extract 'seller_response_date' (ISO YYYY-MM-DD) from the document date.\n"
    "8. CRITICAL: 'complaint_date' is ONLY the date the CONSUMER initially lodged their grievance or ticket (e.g. 2026-02-14 in customer chat). When extracting from a service center quotation or seller rejection email, DO NOT set 'complaint_date' to the email's date. A service center response or rejection is NOT a complaint lodged by the consumer.\n"
    "9. Extract buyer / consumer identity if present: 'customer_name', 'customer_address', 'customer_phone', 'customer_email', and 'seller_address'.\n"
    "10. If an inspection by a service center technician occurred on-site or in-lab, extract 'inspection_date' (YYYY-MM-DD) and 'inspection_findings'.\n"
    "11. Be concise but precise."
)


# ────────────────── Extraction ──────────────────

def heuristic_text_extractor(document_text: str, filename: str) -> CaseExtractionOutput:
    """Fallback text analyzer when LLM API is unavailable.
    Inspects the actual text content of the document using regex patterns.
    """
    if not document_text or len(document_text.strip()) < 10:
        return CaseExtractionOutput(
            raw_evidence_quotes=["Empty or unreadable document content."]
        )

    text_lower = document_text.lower()

    # Check for non-consumer / academic text indicators
    non_consumer = re.search(
        r'\b(experiment|operating system|deadlock|semaphore|paging|algorithm|roll no|lab report|assignment|oops|class\s+\w+|def\s+\w+)\b',
        text_lower
    )

    # Check for consumer indicators
    has_invoice = re.search(r'\b(invoice|tax invoice|bill|cash memo|gstin|receipt|amount paid|order id)\b', text_lower)
    has_warranty = re.search(r'\b(warranty|guarantee|coverage|onsite|replacement)\b', text_lower)
    has_defect = re.search(r'\b(defect|damage|rejection|stopped working|broken|not charging|flicker|lines)\b', text_lower)

    if non_consumer and not (has_invoice or has_warranty):
        return CaseExtractionOutput(
            product_name=None,
            seller_name=None,
            purchase_date=None,
            raw_evidence_quotes=["Document content analyzed: Academic / technical document. No consumer purchase or warranty terms found."]
        )

    # Extract dates (YYYY-MM-DD or DD/MM/YYYY or DD Mon YYYY)
    date_match = re.search(r'\b(20\d\d[-/]\d\d[-/]\d\d|\d\d[-/]\d\d[-/]20\d\d)\b', document_text)
    purchase_date = date_match.group(1) if date_match else None

    # Extract amount
    amt_match = re.search(r'(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d\d)?)', document_text)
    amount_paid = float(amt_match.group(1).replace(",", "")) if amt_match else None

    # Extract warranty months
    war_match = re.search(r'(\d+)\s*(?:month|year)s?\s*(?:warranty|guarantee)', text_lower)
    warranty_months = None
    if war_match:
        val = int(war_match.group(1))
        warranty_months = val * 12 if "year" in war_match.group(0) else val

    # Extract product name heuristically if present
    prod_match = re.search(r'(?:Item|Product|Description|Model)[:\s]+([^\n\r]+)', document_text, re.I)
    product_name = prod_match.group(1).strip() if prod_match else None

    # Extract seller name
    seller_match = re.search(r'(?:Retailer|Seller|Merchant|Sold by)[:\s]+([^\n\r]+)', document_text, re.I)
    seller_name = seller_match.group(1).strip() if seller_match else None

    # Extract customer name, email, phone, address
    cust_match = re.search(r'(?:Customer Name|Customer|Buyer|Purchaser)[:\s]+([A-Z][a-zA-Z\s\.\-]{2,40})', document_text, re.I)
    customer_name = cust_match.group(1).strip() if cust_match else None

    email_match = re.search(r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b', document_text)
    customer_email = email_match.group(1).strip() if email_match else None

    phone_match = re.search(r'(?:Phone|Contact|Mobile)[:\s]*([+\d\s\-\(\)]{10,18})', document_text, re.I)
    customer_phone = phone_match.group(1).strip() if phone_match else None

    addr_match = re.search(r'(?:Billing & Shipping Address|Billing Address|Shipping Address|Address)[:\s]+([^\n\r]+)', document_text, re.I)
    customer_address = addr_match.group(1).strip() if addr_match else None

    return CaseExtractionOutput(
        product_name=product_name,
        seller_name=seller_name,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        customer_address=customer_address,
        purchase_date=purchase_date,
        amount_paid=amount_paid,
        warranty_period_months=warranty_months,
        raw_evidence_quotes=[document_text[:250].strip()] if document_text else []
    )


def extract_facts_from_text(
    document_text: str,
    doc_type: DocumentType,
    filename: str,
) -> CaseExtractionOutput:
    """Extract structured facts from raw document text using Grok LLM or heuristic fallback."""
    try:
        client = get_instructor_client()
        user_message = (
            f"Document type: {doc_type.value}\n"
            f"Filename: {filename}\n\n"
            f"--- DOCUMENT TEXT ---\n{document_text}\n--- END ---"
        )
        result = client.chat.completions.create(
            model=TEXT_MODEL,
            response_model=CaseExtractionOutput,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.0,
        )
        return result
    except Exception:
        # Fall back to content-based heuristic text extraction
        return heuristic_text_extractor(document_text, filename)

    return result


# ────────────────── Conversion to FactItems ──────────────────

# Fields in CaseExtractionOutput that are not individual "facts"
_SKIP_FIELDS = {"raw_evidence_quotes", "currency"}


def extraction_to_fact_items(
    extraction: CaseExtractionOutput,
    doc_type: DocumentType,
    filename: str,
) -> List[FactItem]:
    """Convert a CaseExtractionOutput into a list of FactItem objects.

    Each non-None field becomes a FactItem with source provenance,
    ready for insertion into the Canonical Fact Ledger.

    Args:
        extraction: The structured extraction result.
        doc_type: Document type for provenance tagging.
        filename: Source filename for provenance tagging.

    Returns:
        List of FactItem instances (one per non-null extracted field).
    """
    fact_items: List[FactItem] = []

    for field_name, field_info in extraction.model_fields.items():
        if field_name in _SKIP_FIELDS:
            continue

        value = getattr(extraction, field_name, None)

        # Skip None / empty values
        if value is None:
            continue
        if isinstance(value, (list, dict)) and not value:
            continue

        # Find a supporting raw quote if available
        raw_snippet = None
        if extraction.raw_evidence_quotes:
            # Use the first quote as a generic snippet;
            # more sophisticated matching could be added later.
            raw_snippet = extraction.raw_evidence_quotes[0]

        fact_items.append(
            FactItem(
                field_name=field_name,
                value=value,
                source_doc_type=doc_type,
                source_filename=filename,
                confidence=0.9,
                raw_snippet=raw_snippet,
                verification_status=VerificationStatus.EXTRACTED,
            )
        )

    return fact_items
