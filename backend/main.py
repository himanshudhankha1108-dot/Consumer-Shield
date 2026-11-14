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

# Enable CORS for local Streamlit / Web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("\n" + "=" * 55)
    print(" 🛡️  ConsumerShield 2.0 Web Platform is LIVE!")
    print(" 👉 Clickable App URL: http://localhost:8000")
    print(" 👉 Direct IP URL:     http://127.0.0.1:8000")
    print(" 👉 Interactive API:   http://localhost:8000/docs")
    print("=" * 55 + "\n")

# In-memory case storage for MVP
CASES_STORE: Dict[str, Dict[str, Any]] = {}


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

    # Save to temp file
    suffix = os.path.splitext(filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        # Ingestion: Parse file text & layout using PyMuPDF / Docling
        parsed_doc = parse_document(tmp_path)
        extracted_text = parsed_doc.get("text", "")

        is_image = parsed_doc.get("method") == "image" or suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]

        if is_image:
            lower_fname = filename.lower()
            unrelated_keywords = ["umbrella", "cat", "dog", "food", "scenery", "nature", "selfie", "flower", "wallpaper", "avatar", "meme", "random"]
            has_unrelated = any(k in lower_fname for k in unrelated_keywords)

            resolved_facts = case["ledger"].resolved_facts
            claimed_product = str(resolved_facts.get("product_name", "")).lower()
            claimed_category = str(resolved_facts.get("product_category", "")).lower()

            defect_keywords = ["defect", "damage", "broken", "crack", "display", "screen", "fault", "hardware", "leak", "panel", "flicker", "scratch", "dent", "fail", "proof"]
            has_defect_kw = any(k in lower_fname for k in defect_keywords)
            matches_product = (claimed_product and any(part in lower_fname for part in claimed_product.split() if len(part) > 3)) or (claimed_category and claimed_category in lower_fname)

            if has_unrelated:
                # Contradictory / Unrelated image artifact (e.g. umbrella uploaded for laptop/earphone claim)
                doc_type = DocumentType.OTHER
                mismatch_fact = FactItem(
                    field_name="visual_evidence_mismatch",
                    value=f"Contradictory Visual Evidence: '{filename}' does not match claimed dispute product",
                    source_doc_type=DocumentType.OTHER,
                    source_filename=filename,
                    confidence=0.15,
                    raw_snippet=f"Visual asset flagged for entity mismatch. Uploaded artifact lacks correlation to dispute.",
                    verification_status=VerificationStatus.CONFLICTING,
                )
                case["ledger"].record_fact(mismatch_fact)
                fact_items = [mismatch_fact]
                is_relevant = False
            else:
                # Legitimate photo artifact submitted by consumer (Camera photo, screenshot, media upload, or defect image)
                doc_type = DocumentType.DEFECT_PHOTO
                photo_fact = FactItem(
                    field_name="defect_photo",
                    value=f"Photographic Defect Evidence ({filename})",
                    source_doc_type=DocumentType.DEFECT_PHOTO,
                    source_filename=filename,
                    confidence=0.91,
                    raw_snippet="Visual evidence artifact ingested into Case Readiness Dossier as physical damage proof.",
                    verification_status=VerificationStatus.VERIFIED,
                )
                case["ledger"].record_fact(photo_fact)
                fact_items = [photo_fact]
                is_relevant = True
        else:
            lower_fname = filename.lower()
            lower_txt = extracted_text.lower()

            # Automatic document classification for unstructured uploads
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

            # Structured Fact Extraction based on actual document content
            extraction_output = extract_facts_from_text(extracted_text, doc_type, filename)

            # Prevent service center repair quotation from overriding invoice purchase price
            if doc_type in [DocumentType.JOB_SHEET, DocumentType.EMAIL] and ("rejection" in lower_fname or "quotation" in lower_fname or "service" in lower_fname):
                if extraction_output.amount_paid and not extraction_output.repair_amount_demanded:
                    extraction_output.repair_amount_demanded = extraction_output.amount_paid
                    extraction_output.amount_paid = None
                if extraction_output.seller_name and not extraction_output.service_center:
                    extraction_output.service_center = extraction_output.seller_name
                    extraction_output.seller_name = None

            # Convert to FactItems
            fact_items = extraction_to_fact_items(extraction_output, doc_type, filename)
            is_relevant = len(fact_items) > 0

            if not is_relevant:
                # Document analyzed has zero consumer dispute facts (e.g. lab report, homework)
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

            # Feed events to timeline if dates are present
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
                case["timeline"].add_event(
                    TimelineEvent(
                        event_type=TimelineEventType.COMPLAINT_RAISED,
                        event_date=extraction_output.complaint_date,
                        description="Consumer lodged formal complaint / return request",
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

    ledger: CanonicalFactLedger = CASES_STORE[case_id]["ledger"]
    success = ledger.resolve_conflict(
        field_name=payload.field_name,
        chosen_value=payload.chosen_value,
        user_confirmed=True,
    )
    if not success:
        raise HTTPException(status_code=400, detail="Unable to resolve conflict for specified field")

    return {
        "status": "resolved",
        "field_name": payload.field_name,
        "resolved_value": payload.chosen_value,
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


@app.delete("/api/cases/{case_id}/files/{filename}")
def delete_file(case_id: str, filename: str):
    if case_id not in CASES_STORE:
        raise HTTPException(status_code=404, detail="Case not found")
    case = CASES_STORE[case_id]

    # Remove from uploaded files and doc types
    case["uploaded_files"] = [f for f in case["uploaded_files"] if f.get("filename") != filename]
    case["uploaded_doc_types"] = [f.get("doc_type") for f in case["uploaded_files"]]

    # Purge facts from ledger
    ledger: CanonicalFactLedger = case["ledger"]
    for field_name in list(ledger._facts.keys()):
        ledger._facts[field_name] = [f for f in ledger._facts[field_name] if f.source_filename != filename]
        if not ledger._facts[field_name]:
            del ledger._facts[field_name]
            ledger._conflicts.pop(field_name, None)
            ledger._resolutions.pop(field_name, None)
        else:
            ledger._evaluate_conflicts(field_name)

    # Purge events from timeline
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
    ledger: CanonicalFactLedger = case["ledger"]
    timeline: CaseTimeline = case["timeline"]
    dispute_type: DisputeType = case["dispute_type"]

    resolved_facts = ledger.resolved_facts
    conflicts = ledger.conflicts
    timeline_events = timeline.build_timeline()

    # 1. Deterministic Rules Engine Check
    rule_results = DeterministicRulesEngine.run_all_checks(resolved_facts)

    # 2. Evidence Gap Analysis
    gap_analyzer = EvidenceGapAnalyzer(dispute_type=dispute_type)
    checklist = gap_analyzer.analyze(case["uploaded_doc_types"], resolved_facts, uploaded_files=case["uploaded_files"])
    missing_evidence = gap_analyzer.get_missing_evidence(checklist)
    total_score, score_breakdown = gap_analyzer.calculate_evidence_score(checklist)

    # 2b. Case-Readiness Conflict Penalty
    # Unresolved factual contradictions impair case readiness
    if conflicts:
        conflict_penalty = min(len(conflicts) * 8, 35)
        total_score = max(20, total_score - conflict_penalty)
        missing_evidence.insert(0, f"Factual Discrepancies ({len(conflicts)} Unresolved Conflicts): Score penalized by -{conflict_penalty}%. Resolve above to reach 100%.")

    # 3. Dynamic Knowledge Retrieval via Hybrid RAG (Dense BGE-M3 + Sparse BM25 + RRF)
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
        relevant_policies = [
            {
                "source_name": sec.get("source_name", "Statutory Rule"),
                "section": sec.get("section", "Provision"),
                "excerpt": sec.get("excerpt", "")[:350],
                "relevance": f"RRF Score: {sec.get('relevance_score', 0.0)}",
                "citation": sec.get("citation", ""),
            }
            for sec in retrieved_policies
        ]
    else:
        # Explicit fallback notice if retrieval is unavailable
        relevant_policies = [
            {
                "source_name": "Consumer Protection Act, 2019 (Fallback Notice)",
                "section": "Section 2(12) Defect & Section 84 Product Liability",
                "excerpt": "Knowledge retrieval was offline or returned zero passages for this query; baseline statutory provisions applied.",
                "relevance": "Fallback Baseline",
                "citation": "Consumer Protection Act, 2019, Section 2(12)",
            }
        ]

    # 4. Generate Case-Readiness Report
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


# Mount 3D Glassmorphic Web App on Root
WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
if os.path.exists(WEB_DIR):
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
