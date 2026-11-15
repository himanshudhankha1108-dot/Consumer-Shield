"""
ConsumerShield — FastAPI Backend
Exposes endpoints for Case creation, document upload, analysis, and report retrieval.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, date

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from evidence.schemas import (
    CaseExtractionOutput,
    CaseReadinessReport,
    DisputeType,
    DocumentType,
    FactItem,
    TimelineEvent,
    TimelineEventType,
    VerificationStatus,
)
from evidence.ledger import CanonicalFactLedger
from evidence.timeline import CaseTimeline
from evidence.gap_analyzer import EvidenceGapAnalyzer
from rules.engine import DeterministicRulesEngine
from reports.generator import CaseReportGenerator
from ingestion.parser import parse_document
from ingestion.extractor import extract_facts_from_text, extraction_to_fact_items
from rag.retriever import HybridRetriever
from rag.generator import GroundedLegalGenerator
from rag.conversational import ConversationalLegalRAG

app = FastAPI(
    title="ConsumerShield API",
    description="AI-Powered Consumer Evidence Intelligence & Case-Readiness System API",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    seed_demo_case("CS-2026-NK9")
    seed_demo_case("CS-2026-SAM")
    seed_demo_case("CS-2026-X4")
    print("\n" + "=" * 55)
    print(" 🛡️  ConsumerShield 2.0 Web Platform is LIVE!")
    print(" 👉 Clickable App URL: http://localhost:8000")
    print(" 👉 Direct IP URL:     http://127.0.0.1:8000")
    print(" 👉 Interactive API:   http://localhost:8000/docs")
    print("=" * 55 + "\n")

CASES_STORE: Dict[str, Dict[str, Any]] = {}


def seed_demo_case(case_id: str) -> Optional[Dict[str, Any]]:
    normalized_id = case_id.upper()
    if "NK9" in normalized_id or "NIKE" in normalized_id:
        nike_ledger = CanonicalFactLedger()
        nike_timeline = CaseTimeline()
        nike_facts = [
            ("product_name", "Nike Air Zoom Pegasus (Size 9)", DocumentType.INVOICE, "Order_Invoice.pdf", 0.99),
            ("seller_name", "FashionTrend India (Flipkart)", DocumentType.INVOICE, "Order_Invoice.pdf", 0.98),
            ("purchase_date", "2026-02-05", DocumentType.INVOICE, "Order_Invoice.pdf", 0.99),
            ("delivery_date", "2026-02-08", DocumentType.INVOICE, "Order_Invoice.pdf", 0.98),
            ("amount_paid", 7995.0, DocumentType.INVOICE, "Order_Invoice.pdf", 0.99),
            ("defect_date", "2026-02-08", DocumentType.DEFECT_PHOTO, "Unboxing_Photo.jpg", 0.97),
            ("defect_description", "Received unbranded counterfeit shoes instead of Nike", DocumentType.DEFECT_PHOTO, "Unboxing_Photo.jpg", 0.95),
            ("complaint_date", "2026-02-09", DocumentType.EMAIL, "Customer_Complaint.eml", 0.98),
            ("seller_response", "Return request rejected: Customer claim unverified", DocumentType.EMAIL, "Customer_Complaint.eml", 0.95),
            ("customer_name", "Rahul Sharma", DocumentType.INVOICE, "Order_Invoice.pdf", 0.99),
            ("customer_address", "Flat 402, Green Glen Layout, Bellandur, Bengaluru", DocumentType.INVOICE, "Order_Invoice.pdf", 0.95),
            ("customer_phone", "+91-9876543210", DocumentType.INVOICE, "Order_Invoice.pdf", 0.95),
            ("customer_email", "rahul@example.test", DocumentType.INVOICE, "Order_Invoice.pdf", 0.95),
            ("platform", "Flipkart", DocumentType.INVOICE, "Order_Invoice.pdf", 0.99),
        ]
        for fn, fv, dt, sf, conf in nike_facts:
            nike_ledger.record_fact(FactItem(
                field_name=fn, value=fv, source_doc_type=dt, source_filename=sf,
                confidence=conf, raw_snippet=str(fv), verification_status=VerificationStatus.VERIFIED
            ))
        nike_timeline.add_event(TimelineEvent(event_date=date(2026, 2, 5), event_type=TimelineEventType.PURCHASE, description="Ordered Nike Air Zoom Pegasus for ₹7,995 via Flipkart", source_doc_type=DocumentType.INVOICE, source_filename="Order_Invoice.pdf"))
        nike_timeline.add_event(TimelineEvent(event_date=date(2026, 2, 8), event_type=TimelineEventType.DELIVERY, description="Package delivered by courier", source_doc_type=DocumentType.JOB_SHEET, source_filename="Courier_Tracking.pdf"))
        nike_timeline.add_event(TimelineEvent(event_date=date(2026, 2, 8), event_type=TimelineEventType.DEFECT_DISCOVERED, description="Box contained counterfeit unbranded product instead of Nike", source_doc_type=DocumentType.DEFECT_PHOTO, source_filename="Unboxing_Photo.jpg"))
        nike_timeline.add_event(TimelineEvent(event_date=date(2026, 2, 9), event_type=TimelineEventType.COMPLAINT_RAISED, description="Return lodged within 24 hours of delivery", source_doc_type=DocumentType.EMAIL, source_filename="Customer_Complaint.eml"))
        nike_timeline.add_event(TimelineEvent(event_date=date(2026, 2, 10), event_type=TimelineEventType.SELLER_RESPONSE, description="Return request rejected by seller", source_doc_type=DocumentType.EMAIL, source_filename="Customer_Complaint.eml"))

        case_obj = {
            "case_id": case_id,
            "dispute_type": DisputeType.DENIED_REFUND,
            "title": "Nike Air Zoom Running Shoes",
            "description": "Received counterfeit shoes instead of Nike",
            "created_at": datetime.utcnow(),
            "ledger": nike_ledger,
            "timeline": nike_timeline,
            "uploaded_files": [
                {"filename": "Order_Invoice.pdf", "doc_type": "invoice"},
                {"filename": "Courier_Tracking.pdf", "doc_type": "job_sheet"},
                {"filename": "Unboxing_Photo.jpg", "doc_type": "defect_photo"},
                {"filename": "Customer_Complaint.eml", "doc_type": "email"},
                {"filename": "Flipkart_7Day_Return_Policy.pdf", "doc_type": "return_policy"},
            ],
            "uploaded_doc_types": [DocumentType.INVOICE, DocumentType.DEFECT_PHOTO, DocumentType.EMAIL, DocumentType.JOB_SHEET, DocumentType.RETURN_POLICY],
            "report": None,
        }
        CASES_STORE[case_id] = case_obj
        return case_obj

    elif "SAM" in normalized_id or "SAMSUNG" in normalized_id:
        sam_ledger = CanonicalFactLedger()
        sam_timeline = CaseTimeline()
        sam_facts = [
            ("product_name", "Samsung Crystal 4K 43\" TV", DocumentType.INVOICE, "sample_invoice_samsung_tv.txt", 0.99),
            ("model_number", "UA43CUE60AKLXL", DocumentType.INVOICE, "sample_invoice_samsung_tv.txt", 0.99),
            ("brand", "Samsung", DocumentType.INVOICE, "sample_invoice_samsung_tv.txt", 0.99),
            ("seller_name", "Cloudtail India", DocumentType.INVOICE, "sample_invoice_samsung_tv.txt", 0.98),
            ("platform", "Amazon India", DocumentType.INVOICE, "sample_invoice_samsung_tv.txt", 0.99),
            ("purchase_date", "2026-02-01", DocumentType.INVOICE, "sample_invoice_samsung_tv.txt", 0.99),
            ("delivery_date", "2026-02-04", DocumentType.INVOICE, "sample_invoice_samsung_tv.txt", 0.98),
            ("amount_paid", 34208.20, DocumentType.INVOICE, "sample_invoice_samsung_tv.txt", 0.99),
            ("defect_date", "2026-02-18", DocumentType.DEFECT_PHOTO, "sample_screen_defect.jpg", 0.97),
            ("defect_description", "Display panel manifested vertical green line artifact across screen", DocumentType.DEFECT_PHOTO, "sample_screen_defect.jpg", 0.95),
            ("complaint_date", "2026-02-19", DocumentType.EMAIL, "sample_support_email.txt", 0.98),
            ("seller_response", "Warranty claim REJECTED: Technician cited alleged liquid contact", DocumentType.JOB_SHEET, "sample_service_job_sheet.txt", 0.95),
            ("repair_amount_demanded", 19500.0, DocumentType.JOB_SHEET, "sample_service_job_sheet.txt", 0.98),
            ("warranty_period_months", 24, DocumentType.WARRANTY_CARD, "sample_warranty_samsung.txt", 0.99),
            ("customer_name", "Rahul Sharma", DocumentType.INVOICE, "sample_invoice_samsung_tv.txt", 0.99),
            ("customer_address", "Flat 402, Green Glen Layout, Bellandur, Bengaluru", DocumentType.INVOICE, "sample_invoice_samsung_tv.txt", 0.95),
            ("customer_phone", "+91-9876543210", DocumentType.INVOICE, "sample_invoice_samsung_tv.txt", 0.95),
            ("customer_email", "rahul@example.test", DocumentType.INVOICE, "sample_invoice_samsung_tv.txt", 0.95),
        ]
        for fn, fv, dt, sf, conf in sam_facts:
            sam_ledger.record_fact(FactItem(
                field_name=fn, value=fv, source_doc_type=dt, source_filename=sf,
                confidence=conf, raw_snippet=str(fv), verification_status=VerificationStatus.VERIFIED
            ))
        sam_timeline.add_event(TimelineEvent(event_date=date(2026, 2, 1), event_type=TimelineEventType.PURCHASE, description="Purchased Samsung Crystal 4K 43\" TV for ₹34,208.20 on Amazon India", source_doc_type=DocumentType.INVOICE, source_filename="sample_invoice_samsung_tv.txt"))
        sam_timeline.add_event(TimelineEvent(event_date=date(2026, 2, 4), event_type=TimelineEventType.DELIVERY, description="Product delivered to consumer", source_doc_type=DocumentType.INVOICE, source_filename="sample_invoice_samsung_tv.txt"))
        sam_timeline.add_event(TimelineEvent(event_date=date(2026, 2, 18), event_type=TimelineEventType.DEFECT_DISCOVERED, description="Display panel manifested vertical green line artifact across screen", source_doc_type=DocumentType.DEFECT_PHOTO, source_filename="sample_screen_defect.jpg"))
        sam_timeline.add_event(TimelineEvent(event_date=date(2026, 2, 19), event_type=TimelineEventType.COMPLAINT_RAISED, description="Formal grievance registered with brand support", source_doc_type=DocumentType.EMAIL, source_filename="sample_support_email.txt"))
        sam_timeline.add_event(TimelineEvent(event_date=date(2026, 2, 23), event_type=TimelineEventType.SERVICE_VISIT, description="Technician rejected warranty alleging liquid contact; demanded ₹19,500 + GST", source_doc_type=DocumentType.JOB_SHEET, source_filename="sample_service_job_sheet.txt"))

        case_obj = {
            "case_id": case_id,
            "dispute_type": DisputeType.WARRANTY_REJECTION,
            "title": "Samsung Crystal 4K 43\" TV",
            "description": "Warranty claim repudiated on alleged liquid damage",
            "created_at": datetime.utcnow(),
            "ledger": sam_ledger,
            "timeline": sam_timeline,
            "uploaded_files": [
                {"filename": "sample_invoice_samsung_tv.txt", "doc_type": "invoice"},
                {"filename": "sample_warranty_samsung.txt", "doc_type": "warranty_card"},
                {"filename": "sample_screen_defect.jpg", "doc_type": "defect_photo"},
                {"filename": "sample_service_job_sheet.txt", "doc_type": "job_sheet"},
                {"filename": "sample_support_email.txt", "doc_type": "email"},
            ],
            "uploaded_doc_types": [DocumentType.INVOICE, DocumentType.WARRANTY_CARD, DocumentType.DEFECT_PHOTO, DocumentType.JOB_SHEET, DocumentType.EMAIL],
            "report": None,
        }
        CASES_STORE[case_id] = case_obj
        return case_obj

    elif "X4" in normalized_id or "BOAT" in normalized_id:
        x4_ledger = CanonicalFactLedger()
        x4_timeline = CaseTimeline()
        x4_facts = [
            ("product_name", "boAt Rockerz 450", DocumentType.INVOICE, "Flipkart_Invoice.pdf", 0.99),
            ("seller_name", "RetailNet Online (Flipkart)", DocumentType.INVOICE, "Flipkart_Invoice.pdf", 0.98),
            ("platform", "Flipkart", DocumentType.INVOICE, "Flipkart_Invoice.pdf", 0.99),
            ("purchase_date", "2026-01-10", DocumentType.INVOICE, "Flipkart_Invoice.pdf", 0.99),
            ("delivery_date", "2026-01-14", DocumentType.INVOICE, "Flipkart_Invoice.pdf", 0.98),
            ("amount_paid", 1499.0, DocumentType.INVOICE, "Flipkart_Invoice.pdf", 0.99),
            ("defect_date", "2026-01-28", DocumentType.WHATSAPP, "boAt_Support_Chat.txt", 0.95),
            ("defect_description", "Left ear cup audio channel cut off completely", DocumentType.WHATSAPP, "boAt_Support_Chat.txt", 0.95),
            ("complaint_date", "2026-02-01", DocumentType.WHATSAPP, "boAt_Support_Chat.txt", 0.98),
            ("seller_response", "Refer to manufacturer warranty", DocumentType.WHATSAPP, "boAt_Support_Chat.txt", 0.95),
            ("warranty_period_months", 12, DocumentType.WARRANTY_CARD, "boAt_Warranty_Card.pdf", 0.99),
            ("customer_name", "Rahul Sharma", DocumentType.INVOICE, "Flipkart_Invoice.pdf", 0.99),
            ("customer_address", "Flat 402, Green Glen Layout, Bellandur, Bengaluru", DocumentType.INVOICE, "Flipkart_Invoice.pdf", 0.95),
            ("customer_phone", "+91-9876543210", DocumentType.INVOICE, "Flipkart_Invoice.pdf", 0.95),
            ("customer_email", "rahul@example.test", DocumentType.INVOICE, "Flipkart_Invoice.pdf", 0.95),
        ]
        for fn, fv, dt, sf, conf in x4_facts:
            x4_ledger.record_fact(FactItem(
                field_name=fn, value=fv, source_doc_type=dt, source_filename=sf,
                confidence=conf, raw_snippet=str(fv), verification_status=VerificationStatus.VERIFIED
            ))
        x4_timeline.add_event(TimelineEvent(event_date=date(2026, 1, 10), event_type=TimelineEventType.PURCHASE, description="Purchased boAt Rockerz 450 headphones via Flipkart", source_doc_type=DocumentType.INVOICE, source_filename="Flipkart_Invoice.pdf"))
        x4_timeline.add_event(TimelineEvent(event_date=date(2026, 1, 14), event_type=TimelineEventType.DELIVERY, description="Product delivered to consumer", source_doc_type=DocumentType.INVOICE, source_filename="Flipkart_Invoice.pdf"))
        x4_timeline.add_event(TimelineEvent(event_date=date(2026, 1, 28), event_type=TimelineEventType.DEFECT_DISCOVERED, description="Left ear cup audio channel cut off completely", source_doc_type=DocumentType.WHATSAPP, source_filename="boAt_Support_Chat.txt"))
        x4_timeline.add_event(TimelineEvent(event_date=date(2026, 2, 1), event_type=TimelineEventType.COMPLAINT_RAISED, description="Consumer lodged return request with seller", source_doc_type=DocumentType.WHATSAPP, source_filename="boAt_Support_Chat.txt"))
        x4_timeline.add_event(TimelineEvent(event_date=date(2026, 2, 3), event_type=TimelineEventType.SELLER_RESPONSE, description="Seller directed consumer to brand authorized service", source_doc_type=DocumentType.WHATSAPP, source_filename="boAt_Support_Chat.txt"))

        case_obj = {
            "case_id": case_id,
            "dispute_type": DisputeType.DEFECTIVE_PRODUCT,
            "title": "boAt Rockerz 450",
            "description": "Left ear cup audio channel cut off completely",
            "created_at": datetime.utcnow(),
            "ledger": x4_ledger,
            "timeline": x4_timeline,
            "uploaded_files": [
                {"filename": "Flipkart_Invoice.pdf", "doc_type": "invoice"},
                {"filename": "boAt_Warranty_Card.pdf", "doc_type": "warranty_card"},
                {"filename": "boAt_Support_Chat.txt", "doc_type": "whatsapp"},
            ],
            "uploaded_doc_types": [DocumentType.INVOICE, DocumentType.WARRANTY_CARD, DocumentType.WHATSAPP],
            "report": None,
        }
        CASES_STORE[case_id] = case_obj
        return case_obj
    return None


class CreateCaseRequest(BaseModel):
    dispute_type: DisputeType = DisputeType.DEFECTIVE_PRODUCT
    title: Optional[str] = "Consumer Dispute"
    description: Optional[str] = ""


class CreateCaseResponse(BaseModel):
    case_id: str
    status: str
    dispute_type: DisputeType
    created_at: datetime


class ResolveConflictRequest(BaseModel):
    field_name: str
    chosen_value: Any


class ChatRequest(BaseModel):
    question: str
    chat_history: Optional[List[Dict[str, str]]] = []


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ConsumerShield API",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/rag/health")
def rag_health():
    """Diagnostic health check for the hybrid RAG pipeline."""
    try:
        retriever = HybridRetriever()
        return retriever.health_check()
    except Exception as exc:
        return {"status": "unhealthy", "error": str(exc)}


@app.post("/api/cases", response_model=CreateCaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(payload: CreateCaseRequest):
    case_id = f"CS-{uuid.uuid4().hex[:8].upper()}"
    CASES_STORE[case_id] = {
        "case_id": case_id,
        "dispute_type": payload.dispute_type,
        "title": payload.title,
        "description": payload.description,
        "created_at": datetime.utcnow(),
        "ledger": CanonicalFactLedger(),
        "timeline": CaseTimeline(),
        "uploaded_files": [],
        "uploaded_doc_types": [],
        "report": None,
    }
    return CreateCaseResponse(
        case_id=case_id,
        status="created",
        dispute_type=payload.dispute_type,
        created_at=CASES_STORE[case_id]["created_at"],
    )


@app.get("/api/cases")
def list_cases():
    return [
        {
            "case_id": c["case_id"],
            "title": c["title"],
            "dispute_type": c["dispute_type"],
            "created_at": c["created_at"].isoformat(),
            "files_count": len(c["uploaded_files"]),
            "has_report": c["report"] is not None,
        }
        for c in CASES_STORE.values()
    ]


@app.get("/api/cases/{case_id}")
def get_case_details(case_id: str):
    if case_id not in CASES_STORE:
        raise HTTPException(status_code=404, detail="Case not found")
    c = CASES_STORE[case_id]
    return {
        "case_id": c["case_id"],
        "title": c["title"],
        "dispute_type": c["dispute_type"],
        "description": c["description"],
        "created_at": c["created_at"].isoformat(),
        "uploaded_files": c["uploaded_files"],
        "ledger_summary": c["ledger"].get_summary(),
        "timeline_events": [e.model_dump() for e in c["timeline"].build_timeline()],
        "has_report": c["report"] is not None,
    }


@app.post("/api/cases/{case_id}/upload")
async def upload_evidence(
    case_id: str,
    file: UploadFile = File(...),
    doc_type: Optional[DocumentType] = DocumentType.OTHER,
):
    if case_id not in CASES_STORE:
        CASES_STORE[case_id] = {
            "case_id": case_id,
            "dispute_type": DisputeType.DEFECTIVE_PRODUCT,
            "title": "Active Case",
            "description": "",
            "created_at": datetime.utcnow(),
            "ledger": CanonicalFactLedger(),
            "timeline": CaseTimeline(),
            "uploaded_files": [],
            "uploaded_doc_types": [],
            "report": None,
        }

    case = CASES_STORE[case_id]
    filename = file.filename or "uploaded_file"

    suffix = os.path.splitext(filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        parsed_doc = parse_document(tmp_path)
        extracted_text = parsed_doc.get("text", "")

        is_image = parsed_doc.get("method") == "image" or suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]

        if is_image:
            from ingestion.vision_parser import analyze_product_image

            expected_prod = case.get("product") or case["ledger"].resolved_facts.get("product_name")
            extracted_data = analyze_product_image(tmp_path, expected_product=expected_prod)

            if not extracted_data.is_relevant_to_case:
                doc_type = DocumentType.OTHER
                detected_obj = extracted_data.detected_primary_object or "Unrelated Object"
                red_flag_val = f"Red Flag: Irrelevant Image Detected ({detected_obj})"
                mismatch_fact = FactItem(
                    field_name="visual_evidence_mismatch",
                    value=red_flag_val,
                    source_doc_type=DocumentType.OTHER,
                    source_filename=filename,
                    confidence=0.10,
                    raw_snippet=f"Forensic visual analysis confirmed non-consumer artifact '{detected_obj}'. Excluded from Case Readiness Dossier.",
                    verification_status=VerificationStatus.CONFLICTING,
                )
                case["ledger"].record_fact(mismatch_fact)
                fact_items = [mismatch_fact]
                is_relevant = False
            else:
                primary_obj = extracted_data.detected_primary_object or "Consumer Hardware"
                desc = extracted_data.defect_description or "Physical damage or defect verified via visual inspection"

                is_mismatch = False
                mismatch_note = ""
                if expected_prod and extracted_data.is_product_match is False:
                    is_mismatch = True
                    conf_pct = int((extracted_data.product_match_confidence or 0.0) * 100)
                    mismatch_note = (
                        f"Visual discrepancy: Uploaded photo shows {primary_obj}, "
                        f"which does not match declared product '{expected_prod}' (match confidence: {conf_pct}%)"
                    )

                if is_mismatch:
                    doc_type = DocumentType.OTHER
                    red_flag_val = f"Red Flag: Product Discrepancy Detected ({mismatch_note})"
                    mismatch_fact = FactItem(
                        field_name="visual_product_mismatch",
                        value=red_flag_val,
                        source_doc_type=DocumentType.OTHER,
                        source_filename=filename,
                        confidence=0.20,
                        raw_snippet=mismatch_note,
                        verification_status=VerificationStatus.CONFLICTING,
                    )
                    case["ledger"].record_fact(mismatch_fact)
                    fact_items = [mismatch_fact]
                    is_relevant = False
                else:
                    doc_type = DocumentType.DEFECT_PHOTO
                    photo_fact = FactItem(
                        field_name="defect_photo",
                        value=f"Photographic Defect Evidence: {primary_obj} ({desc})",
                        source_doc_type=DocumentType.DEFECT_PHOTO,
                        source_filename=filename,
                        confidence=0.95,
                        raw_snippet=f"Visual evidence verified by forensic analysis: {desc}",
                        verification_status=VerificationStatus.VERIFIED,
                    )
                    case["ledger"].record_fact(photo_fact)
                    fact_items = [photo_fact]
                    is_relevant = True
        else:
            lower_fname = filename.lower()
            lower_txt = extracted_text.lower()

            if doc_type == DocumentType.OTHER:
                if any(k in lower_fname for k in ["invoice", "bill", "receipt", "memo"]) or "tax invoice" in lower_txt:
                    doc_type = DocumentType.INVOICE
                elif any(k in lower_fname for k in ["warranty", "guarantee"]) or "warranty certificate" in lower_txt:
                    doc_type = DocumentType.WARRANTY_CARD
                elif any(k in lower_fname for k in ["whatsapp", "chat"]) or parsed_doc.get("method") == "chat_export":
                    doc_type = DocumentType.WHATSAPP
                elif any(k in lower_fname for k in ["rejection", "job_sheet", "inspection", "quotation"]):
                    doc_type = DocumentType.JOB_SHEET
                elif any(k in lower_fname for k in ["email", "mail"]):
                    doc_type = DocumentType.EMAIL

            extraction_output = extract_facts_from_text(extracted_text, doc_type, filename)

            if doc_type in [DocumentType.JOB_SHEET, DocumentType.EMAIL] and ("rejection" in lower_fname or "quotation" in lower_fname or "service" in lower_fname):
                if extraction_output.amount_paid and not extraction_output.repair_amount_demanded:
                    extraction_output.repair_amount_demanded = extraction_output.amount_paid
                    extraction_output.amount_paid = None
                if extraction_output.seller_name and not extraction_output.service_center:
                    extraction_output.service_center = extraction_output.seller_name
                    extraction_output.seller_name = None

            fact_items = extraction_to_fact_items(extraction_output, doc_type, filename)
            is_relevant = len(fact_items) > 0

            if not is_relevant:
                audit_fact = FactItem(
                    field_name="document_audit",
                    value=f"Non-dispute document: No purchase, price, or warranty clauses identified in content",
                    source_doc_type=doc_type,
                    source_filename=filename,
                    confidence=0.12,
                    raw_snippet=extracted_text[:150] if extracted_text else "",
                    verification_status=VerificationStatus.CONFLICTING,
                )
                case["ledger"].record_fact(audit_fact)
                fact_items = [audit_fact]
            else:
                for fact in fact_items:
                    case["ledger"].record_fact(fact)

            if doc_type in (DocumentType.EMAIL, DocumentType.JOB_SHEET):
                has_rejection_clues = bool(extraction_output.repair_amount_demanded or extraction_output.warranty_exclusions or (extraction_output.resolution_offered and any(w in str(extraction_output.resolution_offered).lower() for w in ["reject", "denied", "payment"])))
                if has_rejection_clues and not extraction_output.seller_response:
                    excl = extraction_output.warranty_exclusions or "alleged external factors"
                    demand_str = f" demanding payment of {extraction_output.currency or 'INR'} {extraction_output.repair_amount_demanded}" if extraction_output.repair_amount_demanded else ""
                    extraction_output.seller_response = f"Free warranty repair REJECTED citing {excl}{demand_str}"
                    case["ledger"].record_fact(
                        FactItem(
                            field_name="seller_response",
                            value=extraction_output.seller_response,
                            source_doc_type=doc_type,
                            source_filename=filename,
                            confidence=0.95,
                        )
                    )

                if extraction_output.seller_response and not extraction_output.seller_response_date:
                    import re
                    from dateutil import parser as dparser
                    date_m = re.search(r'\b(20\d\d[-/]\d\d[-/]\d\d|\d{1,2}\s+[A-Za-z]{3,9}\s+20\d\d|\d{1,2}[-/]\d{1,2}[-/]20\d\d)\b', extracted_text)
                    if date_m:
                        try:
                            parsed_d = dparser.parse(date_m.group(1), fuzzy=True).date()
                            extraction_output.seller_response_date = parsed_d.isoformat()
                            case["ledger"].record_fact(
                                FactItem(
                                    field_name="seller_response_date",
                                    value=extraction_output.seller_response_date,
                                    source_doc_type=doc_type,
                                    source_filename=filename,
                                    confidence=0.95,
                                )
                            )
                        except Exception:
                            pass

            if extraction_output.purchase_date:
                case["timeline"].add_event(
                    TimelineEvent(
                        event_type=TimelineEventType.PURCHASE,
                        event_date=extraction_output.purchase_date,
                        description=f"Purchased {extraction_output.product_name or 'product'} from {extraction_output.seller_name or 'seller'}",
                        source_doc_type=doc_type,
                        source_filename=filename,
                    )
                )
            if extraction_output.delivery_date:
                case["timeline"].add_event(
                    TimelineEvent(
                        event_type=TimelineEventType.DELIVERY,
                        event_date=extraction_output.delivery_date,
                        description="Product delivered to consumer",
                        source_doc_type=doc_type,
                        source_filename=filename,
                    )
                )
            if extraction_output.defect_date:
                case["timeline"].add_event(
                    TimelineEvent(
                        event_type=TimelineEventType.DEFECT_DISCOVERED,
                        event_date=extraction_output.defect_date,
                        description=f"Defect identified: {extraction_output.defect_description or 'Reported issue'}",
                        source_doc_type=doc_type,
                        source_filename=filename,
                    )
                )
            if extraction_output.complaint_date:
                is_seller_rejection = doc_type in (DocumentType.EMAIL, DocumentType.JOB_SHEET) and bool(extraction_output.seller_response or extraction_output.repair_amount_demanded)
                if not is_seller_rejection or (extraction_output.complaint_date != extraction_output.seller_response_date):
                    case["timeline"].add_event(
                        TimelineEvent(
                            event_type=TimelineEventType.COMPLAINT_RAISED,
                            event_date=extraction_output.complaint_date,
                            description="Consumer lodged formal complaint / return request",
                            source_doc_type=doc_type,
                            source_filename=filename,
                        )
                    )

            insp_date = extraction_output.inspection_date
            if not insp_date and doc_type in (DocumentType.JOB_SHEET, DocumentType.EMAIL):
                insp_m = re.search(r'(?:inspected onsite by our technician on|inspected on|technician visit(?:ed)? on|inspection date:?)\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+20\d\d|20\d\d[-/]\d\d[-/]\d\d)', extracted_text, re.I)
                if insp_m:
                    try:
                        from dateutil import parser as dparser
                        insp_date = dparser.parse(insp_m.group(1), fuzzy=True).date().isoformat()
                    except Exception:
                        pass
            if insp_date:
                insp_findings = extraction_output.inspection_findings or extraction_output.defect_description or "technical assessment"
                case["timeline"].add_event(
                    TimelineEvent(
                        event_type=TimelineEventType.SERVICE_VISIT,
                        event_date=insp_date,
                        description=f"Technical inspection: Service technician inspected product ({insp_findings})",
                        source_doc_type=doc_type,
                        source_filename=filename,
                    )
                )

            if extraction_output.seller_response_date or extraction_output.seller_response:
                case["timeline"].add_event(
                    TimelineEvent(
                        event_type=TimelineEventType.SELLER_RESPONSE,
                        event_date=extraction_output.seller_response_date,
                        description=f"Seller response: {extraction_output.seller_response or 'Response received'}",
                        source_doc_type=doc_type,
                        source_filename=filename,
                    )
                )

        case["uploaded_files"].append(
            {
                "filename": filename,
                "doc_type": doc_type.value,
                "extraction_method": parsed_doc.get("method", "unknown"),
                "chars_extracted": len(extracted_text),
                "facts_count": len(fact_items),
            }
        )
        case["uploaded_doc_types"].append(doc_type)

        all_ledger_facts = [
            {
                "field": f.field_name,
                "value": str(f.value),
                "source": f.source_filename,
                "confidence": f.confidence,
                "status": f.verification_status.value,
            }
            for items in case["ledger"]._facts.values()
            for f in items
        ]
        active_conflicts = [
            {
                "field": c.field,
                "options": c.values,
            }
            for c in case["ledger"].conflicts
        ]

        return {
            "status": "success",
            "filename": filename,
            "is_relevant": is_relevant,
            "doc_type": doc_type,
            "extracted_text_preview": extracted_text[:250],
            "facts": [
                {
                    "field": f.field_name,
                    "value": str(f.value),
                    "source": f.source_filename,
                    "confidence": f.confidence,
                    "status": f.verification_status.value,
                }
                for f in fact_items
            ],
            "all_facts": all_ledger_facts,
            "canonical_facts": case["ledger"].canonical_records,
            "resolved_facts": case["ledger"].resolved_facts,
            "conflicts": active_conflicts,
            "conflicts_detected": len(case["ledger"].conflicts),
        }

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post("/api/cases/{case_id}/resolve-conflict")
def resolve_conflict(case_id: str, payload: ResolveConflictRequest):
    if case_id not in CASES_STORE:
        raise HTTPException(status_code=404, detail="Case not found")

    case = CASES_STORE[case_id]
    ledger: CanonicalFactLedger = case["ledger"]
    success = ledger.resolve_conflict(
        field_name=payload.field_name,
        chosen_value=payload.chosen_value,
        user_confirmed=True,
    )
    if not success:
        raise HTTPException(status_code=400, detail="Unable to resolve conflict for specified field")

    gap_analyzer = EvidenceGapAnalyzer(dispute_type=case["dispute_type"])
    checklist = gap_analyzer.analyze(
        case["uploaded_doc_types"],
        ledger.resolved_facts,
        uploaded_files=case["uploaded_files"]
    )
    missing_evidence = gap_analyzer.get_missing_evidence(checklist)
    total_score, score_breakdown = gap_analyzer.calculate_evidence_score(checklist)

    active_conflicts = ledger.conflicts
    if active_conflicts:
        conflict_penalty = min(len(active_conflicts) * 8, 35)
        total_score = max(20, total_score - conflict_penalty)
        missing_evidence.insert(0, f"Factual Discrepancies ({len(active_conflicts)} Unresolved Conflicts): Score penalized by -{conflict_penalty}%. Resolve above to reach 100%.")

    if "analysis_result" in case and case["analysis_result"]:
        case["analysis_result"]["total_score"] = total_score
        case["analysis_result"]["score_breakdown"] = score_breakdown
        case["analysis_result"]["missing_evidence"] = missing_evidence
        case["analysis_result"]["conflicts"] = [
            {"field": c.field, "options": c.values} for c in active_conflicts
        ]

    return {
        "status": "resolved",
        "field_name": payload.field_name,
        "resolved_value": payload.chosen_value,
        "total_score": total_score,
        "score_breakdown": [d.model_dump() for d in score_breakdown],
        "missing_evidence": missing_evidence,
        "all_facts": [
            {
                "field": f.field_name,
                "value": str(f.value),
                "source": f.source_filename,
                "confidence": f.confidence,
                "status": f.verification_status.value,
            }
            for items in ledger._facts.values()
            for f in items
        ],
        "canonical_facts": ledger.canonical_records,
        "resolved_facts": ledger.resolved_facts,
        "conflicts": [
            {
                "field": c.field,
                "options": c.values,
            }
            for c in active_conflicts
        ],
    }


@app.delete("/api/cases/{case_id}/files/{filename}")
def delete_file(case_id: str, filename: str):
    if case_id not in CASES_STORE:
        raise HTTPException(status_code=404, detail="Case not found")
    case = CASES_STORE[case_id]

    case["uploaded_files"] = [f for f in case["uploaded_files"] if f.get("filename") != filename]
    case["uploaded_doc_types"] = [f.get("doc_type") for f in case["uploaded_files"]]

    ledger: CanonicalFactLedger = case["ledger"]
    for field_name in list(ledger._facts.keys()):
        ledger._facts[field_name] = [f for f in ledger._facts[field_name] if f.source_filename != filename]
        if not ledger._facts[field_name]:
            del ledger._facts[field_name]
            ledger._conflicts.pop(field_name, None)
            ledger._resolutions.pop(field_name, None)
        else:
            ledger._evaluate_conflicts(field_name)

    timeline: CaseTimeline = case["timeline"]
    timeline._events = [e for e in timeline._events if e.source_filename != filename]

    return {
        "status": "deleted",
        "filename": filename,
        "remaining_files": len(case["uploaded_files"]),
        "conflicts_count": len(ledger.conflicts),
        "facts_count": sum(len(v) for v in ledger._facts.values()),
        "all_facts": [
            {
                "field": f.field_name,
                "value": str(f.value),
                "source": f.source_filename,
                "confidence": f.confidence,
                "status": f.verification_status.value,
            }
            for items in ledger._facts.values()
            for f in items
        ],
        "canonical_facts": ledger.canonical_records,
        "resolved_facts": ledger.resolved_facts,
        "conflicts": [
            {
                "field": c.field,
                "options": c.values,
            }
            for c in ledger.conflicts
        ],
    }


@app.post("/api/cases/{case_id}/analyze")
def analyze_case(case_id: str):
    if case_id not in CASES_STORE or len(CASES_STORE[case_id]["ledger"]._facts) == 0:
        demo_seeded = seed_demo_case(case_id)
        if not demo_seeded and case_id not in CASES_STORE:
            CASES_STORE[case_id] = {
                "case_id": case_id,
                "dispute_type": DisputeType.DEFECTIVE_PRODUCT,
                "title": "Active Case",
                "description": "",
                "created_at": datetime.utcnow(),
                "ledger": CanonicalFactLedger(),
                "timeline": CaseTimeline(),
                "uploaded_files": [],
                "uploaded_doc_types": [],
                "report": None,
            }

    case = CASES_STORE[case_id]
    ledger: CanonicalFactLedger = case["ledger"]
    timeline: CaseTimeline = case["timeline"]
    dispute_type: DisputeType = case["dispute_type"]

    resolved_facts = ledger.resolved_facts
    conflicts = ledger.conflicts
    timeline_events = timeline.build_timeline()

    rule_results = DeterministicRulesEngine.run_all_checks(resolved_facts)

    gap_analyzer = EvidenceGapAnalyzer(dispute_type=dispute_type)
    checklist = gap_analyzer.analyze(case["uploaded_doc_types"], resolved_facts, uploaded_files=case["uploaded_files"])
    missing_evidence = gap_analyzer.get_missing_evidence(checklist)
    total_score, score_breakdown = gap_analyzer.calculate_evidence_score(checklist)

    if conflicts:
        conflict_penalty = min(len(conflicts) * 8, 35)
        total_score = max(20, total_score - conflict_penalty)
        missing_evidence.insert(0, f"Factual Discrepancies ({len(conflicts)} Unresolved Conflicts): Score penalized by -{conflict_penalty}%. Resolve above to reach 100%.")

    retrieval_query = (
        f"{dispute_type.value} {resolved_facts.get('product_name', '')} "
        f"{resolved_facts.get('defect_description', '')} {resolved_facts.get('seller_response', '')} "
        f"{resolved_facts.get('resolution_offered', '')}"
    ).strip()

    ref_date = None
    date_candidates = [resolved_facts.get("defect_date"), resolved_facts.get("complaint_date"), resolved_facts.get("purchase_date")]
    for cand in date_candidates:
        if cand:
            try:
                ref_date = date.fromisoformat(str(cand)[:10])
                break
            except Exception:
                pass

    try:
        retriever = HybridRetriever()
        rag_context = retriever.retrieve_context(
            query=retrieval_query,
            reference_date=ref_date,
            top_k=4,
        )
        retrieved_policies = rag_context.get("sections", [])
    except Exception as exc:
        retrieved_policies = []

    if retrieved_policies:
        relevant_policies = []
        is_delivered_defect = bool(
            resolved_facts.get("delivery_date")
            or resolved_facts.get("defect_date")
            or dispute_type in (DisputeType.DEFECTIVE_PRODUCT, DisputeType.WARRANTY_REJECTION)
        )
        for sec in retrieved_policies:
            sec_title = str(sec.get("section", "")).lower()
            src_title = str(sec.get("source_name", "")).lower()
            excerpt_txt = str(sec.get("excerpt", "")).lower()
            if is_delivered_defect:
                if any(k in sec_title or k in excerpt_txt for k in [
                    "cancellation & pre-dispatch", "pre-dispatch", "fashion & lifestyle", "innerwear",
                    "replacement window", "return window", "7 days from the confirmed date"
                ]):
                    continue
            relevant_policies.append(
                {
                    "source_name": sec.get("source_name", "Statutory Rule"),
                    "section": sec.get("section", "Provision"),
                    "excerpt": sec.get("excerpt", "")[:350],
                    "relevance": f"RRF Score: {sec.get('relevance_score', 0.0)}",
                    "citation": sec.get("citation", ""),
                }
            )
        if not relevant_policies:
            relevant_policies = [
                {
                    "source_name": "Consumer Protection Act, 2019",
                    "section": "Section 84 (Liability of Product Manufacturer)",
                    "excerpt": "A product manufacturer shall be liable in a product liability action, if the product contains a manufacturing defect, or is defective in design, or there is a deviation from manufacturing specifications, or the product does not conform to the express warranty.",
                    "relevance": "Direct Statutory Application",
                    "citation": "Consumer Protection Act, 2019, Section 84",
                }
            ]
    else:
        relevant_policies = [
            {
                "source_name": "Consumer Protection Act, 2019 (Fallback Notice)",
                "section": "Section 2(12) Defect & Section 84 Product Liability",
                "excerpt": "Knowledge retrieval was offline or returned zero passages for this query; baseline statutory provisions applied.",
                "relevance": "Fallback Baseline",
                "citation": "Consumer Protection Act, 2019, Section 2(12)",
            }
        ]

    report_gen = CaseReportGenerator(case_id=case_id)
    report: CaseReadinessReport = report_gen.generate_report(
        resolved_facts=resolved_facts,
        conflicts=conflicts,
        timeline_events=timeline_events,
        evidence_checklist=checklist,
        rule_results=rule_results,
        relevant_policies=relevant_policies,
        score=total_score,
        max_score=100,
        score_breakdown=score_breakdown,
        missing_evidence=missing_evidence,
        dispute_type=dispute_type,
    )
    report.draft_complaint = report_gen.generate_complaint_draft(report)

    case["report"] = report
    return report_gen.report_to_dict(report)


@app.get("/api/cases/{case_id}/report")
def get_report(case_id: str):
    if case_id not in CASES_STORE:
        raise HTTPException(status_code=404, detail="Case not found")
    report = CASES_STORE[case_id].get("report")
    if not report:
        raise HTTPException(status_code=404, detail="Report not generated yet. Run /analyze first.")

    report_gen = CaseReportGenerator(case_id=case_id)
    return report_gen.report_to_dict(report)


@app.post("/api/cases/{case_id}/chat")
def case_chat(case_id: str, payload: ChatRequest):
    """Conversational legal query grounded in case facts and retrieved statutory provisions."""
    if case_id not in CASES_STORE:
        raise HTTPException(status_code=404, detail="Case not found")
    case = CASES_STORE[case_id]
    ledger: CanonicalFactLedger = case["ledger"]
    resolved_facts = ledger.resolved_facts

    assistant = ConversationalLegalRAG()
    return assistant.answer_question(
        question=payload.question,
        case_facts=resolved_facts,
        chat_history=payload.chat_history,
    )


WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
if os.path.exists(WEB_DIR):
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
