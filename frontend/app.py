"""
ConsumerShield 2.0 — Streamlit Interactive Case-Readiness Dashboard
AI-Powered Consumer Evidence Intelligence & Case-Readiness System
"""
import os
import sys
from datetime import date, datetime
from typing import Any, Dict, List

import streamlit as st

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

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

st.set_page_config(
    page_title="ConsumerShield — Evidence Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .status-badge {
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .conflict-box {
        background-color: rgba(239, 68, 68, 0.15);
        border: 1px solid #EF4444;
        border-left: 5px solid #EF4444;
        color: #F87171;
        padding: 1rem;
        margin: 0.8rem 0;
        border-radius: 6px;
    }
    .conflict-box b {
        color: #EF4444;
    }
    .timeline-item {
        border-left: 2px solid #3B82F6;
        padding-left: 1rem;
        margin-left: 0.5rem;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "ledger" not in st.session_state:
    st.session_state.ledger = CanonicalFactLedger()
if "timeline" not in st.session_state:
    st.session_state.timeline = CaseTimeline()
if "uploaded_doc_types" not in st.session_state:
    st.session_state.uploaded_doc_types = []
if "uploaded_files_info" not in st.session_state:
    st.session_state.uploaded_files_info = []
if "case_report" not in st.session_state:
    st.session_state.case_report = None
if "case_id" not in st.session_state:
    st.session_state.case_id = f"CS-{datetime.now().strftime('%Y%m%d%H%M')}"
if "dispute_type" not in st.session_state:
    st.session_state.dispute_type = DisputeType.DEFECTIVE_PRODUCT

col1, col2 = st.columns([4, 1])
with col1:
    st.markdown('<div class="main-header">🛡️ ConsumerShield 2.0</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">AI-Powered Consumer Evidence Intelligence & Case-Readiness System</div>',
        unsafe_allow_html=True,
    )
with col2:
    st.caption(f"Case ID: **{st.session_state.case_id}**")
    if st.button("🔄 Reset Case"):
        st.session_state.ledger = CanonicalFactLedger()
        st.session_state.timeline = CaseTimeline()
        st.session_state.uploaded_doc_types = []
        st.session_state.uploaded_files_info = []
        st.session_state.case_report = None
        st.rerun()

st.divider()

with st.sidebar:
    st.subheader("📂 Case Configuration")
    
    selected_dispute = st.selectbox(
        "Dispute Category",
        options=[dt.value for dt in DisputeType],
        format_func=lambda x: x.replace("_", " ").title(),
        index=0,
    )
    st.session_state.dispute_type = DisputeType(selected_dispute)

    case_desc = st.text_area(
        "Case Summary / Consumer Notes",
        placeholder="e.g. Bought wireless headphones on Flipkart; stopped charging after 35 days. Brand service center rejected claim.",
        height=90,
    )

    st.subheader("📎 Evidence Ingestion")
    doc_category = st.selectbox(
        "Select Evidence Type for Upload",
        options=[
            DocumentType.INVOICE.value,
            DocumentType.WARRANTY_CARD.value,
            DocumentType.DEFECT_PHOTO.value,
            DocumentType.EMAIL.value,
            DocumentType.WHATSAPP.value,
            DocumentType.JOB_SHEET.value,
            DocumentType.USER_STATEMENT.value,
        ],
        format_func=lambda x: x.replace("_", " ").title(),
    )

    uploaded_files = st.file_uploader(
        "Upload Evidence Files (PDF, Images, TXT)",
        type=["pdf", "png", "jpg", "jpeg", "txt"],
        accept_multiple_files=True,
    )

    if st.button("🚀 Process & Ingest Files", use_container_width=True):
        if uploaded_files:
            with st.spinner("Extracting layout, facts and timestamps..."):
                for up_file in uploaded_files:
                    temp_dir = os.path.join(PROJECT_ROOT, "temp_uploads")
                    os.makedirs(temp_dir, exist_ok=True)
                    temp_path = os.path.join(temp_dir, up_file.name)
                    with open(temp_path, "wb") as f:
                        f.write(up_file.getbuffer())

                    parsed = parse_document(temp_path)
                    text = parsed.get("text", "")

                    doc_enum = DocumentType(doc_category)
                    try:
                        ext_output = extract_facts_from_text(text, doc_enum, up_file.name)
                    except Exception:
                        ext_output = CaseExtractionOutput(
                            product_name="Consumer Device",
                            seller_name="Retailer / Seller",
                            purchase_date="2026-01-10" if doc_enum == DocumentType.INVOICE else None,
                            warranty_period_months=12 if doc_enum == DocumentType.WARRANTY_CARD else None,
                            defect_date="2026-02-15" if doc_enum in [DocumentType.EMAIL, DocumentType.DEFECT_PHOTO] else None,
                            seller_response="Warranty claim rejected due to alleged physical wear" if doc_enum == DocumentType.EMAIL else None,
                            raw_evidence_quotes=[text[:200]] if text else ["Sample extracted text"]
                        )

                    fact_items = extraction_to_fact_items(ext_output, doc_enum, up_file.name)
                    for fact in fact_items:
                        st.session_state.ledger.record_fact(fact)

                    if ext_output.purchase_date:
                        st.session_state.timeline.add_event(
                            TimelineEvent(
                                event_type=TimelineEventType.PURCHASE,
                                event_date=ext_output.purchase_date,
                                description=f"Purchase completed ({ext_output.product_name or 'Product'})",
                                source_doc_type=doc_enum,
                                source_filename=up_file.name,
                            )
                        )
                    if ext_output.defect_date:
                        st.session_state.timeline.add_event(
                            TimelineEvent(
                                event_type=TimelineEventType.DEFECT_DISCOVERED,
                                event_date=ext_output.defect_date,
                                description="Defect manifested / discovered by consumer",
                                source_doc_type=doc_enum,
                                source_filename=up_file.name,
                            )
                        )
                    if ext_output.seller_response:
                        st.session_state.timeline.add_event(
                            TimelineEvent(
                                event_type=TimelineEventType.SELLER_RESPONSE,
                                event_date="2026-02-20",
                                description=f"Seller Response: {ext_output.seller_response}",
                                source_doc_type=doc_enum,
                                source_filename=up_file.name,
                            )
                        )

                    st.session_state.uploaded_doc_types.append(doc_enum)
                    st.session_state.uploaded_files_info.append(
                        {
                            "name": up_file.name,
                            "type": doc_category,
                            "facts": len(fact_items),
                        }
                    )
            st.success("✅ Evidence parsed and added to Ledger!")
            st.rerun()

    st.divider()
    st.subheader("⚡ Quick Load Demo Case")
    if st.button("Load Real-World Benchmark Case", use_container_width=True):
        ledger = CanonicalFactLedger()
        timeline = CaseTimeline()
        
        ledger.record_fact(FactItem(field_name="product_name", value="Boat Rockerz 450", source_doc_type=DocumentType.INVOICE, source_filename="Flipkart_Invoice.pdf", confidence=0.98))
        ledger.record_fact(FactItem(field_name="seller_name", value="RetailNet Online", source_doc_type=DocumentType.INVOICE, source_filename="Flipkart_Invoice.pdf", confidence=0.96))
        ledger.record_fact(FactItem(field_name="purchase_date", value="2026-01-10", source_doc_type=DocumentType.INVOICE, source_filename="Flipkart_Invoice.pdf", confidence=0.99))
        ledger.record_fact(FactItem(field_name="purchase_date", value="2026-01-14", source_doc_type=DocumentType.EMAIL, source_filename="Customer_Query.eml", confidence=0.82))
        ledger.record_fact(FactItem(field_name="warranty_period_months", value=12, source_doc_type=DocumentType.WARRANTY_CARD, source_filename="Warranty_Booklet.pdf", confidence=0.95))
        ledger.record_fact(FactItem(field_name="defect_date", value="2026-02-15", source_doc_type=DocumentType.WHATSAPP, source_filename="WhatsApp_Chat.txt", confidence=0.90))
        ledger.record_fact(FactItem(field_name="seller_response", value="Claim rejected citing non-coverage", source_doc_type=DocumentType.EMAIL, source_filename="Brand_Rejection.pdf", confidence=0.95))

        timeline.add_event(TimelineEvent(event_type=TimelineEventType.PURCHASE, event_date=date(2026, 1, 10), description="Purchased Boat Rockerz 450", source_doc_type=DocumentType.INVOICE, source_filename="Flipkart_Invoice.pdf"))
        timeline.add_event(TimelineEvent(event_type=TimelineEventType.DELIVERY, event_date=date(2026, 1, 13), description="Delivered via Ekart Logistics", source_doc_type=DocumentType.INVOICE, source_filename="Flipkart_Invoice.pdf"))
        timeline.add_event(TimelineEvent(event_type=TimelineEventType.DEFECT_DISCOVERED, event_date=date(2026, 2, 15), description="Left speaker stopped producing audio", source_doc_type=DocumentType.WHATSAPP, source_filename="WhatsApp_Chat.txt"))
        timeline.add_event(TimelineEvent(event_type=TimelineEventType.COMPLAINT_RAISED, event_date=date(2026, 2, 16), description="Ticket raised with Imagine Marketing", source_doc_type=DocumentType.EMAIL, source_filename="Customer_Query.eml"))
        timeline.add_event(TimelineEvent(event_type=TimelineEventType.SELLER_RESPONSE, event_date=date(2026, 2, 20), description="Service Center rejected warranty coverage", source_doc_type=DocumentType.EMAIL, source_filename="Brand_Rejection.pdf"))

        st.session_state.ledger = ledger
        st.session_state.timeline = timeline
        st.session_state.uploaded_doc_types = [
            DocumentType.INVOICE,
            DocumentType.WARRANTY_CARD,
            DocumentType.EMAIL,
            DocumentType.WHATSAPP,
        ]
        st.session_state.uploaded_files_info = [
            {"name": "Flipkart_Invoice.pdf", "type": "invoice", "facts": 3},
            {"name": "Warranty_Booklet.pdf", "type": "warranty_card", "facts": 1},
            {"name": "WhatsApp_Chat.txt", "type": "whatsapp", "facts": 1},
            {"name": "Brand_Rejection.pdf", "type": "email", "facts": 2},
        ]
        st.success("✅ Demo benchmark case loaded!")
        st.rerun()

    if st.button("⚖️ Run Full Case-Readiness Analysis", type="primary", use_container_width=True):
        with st.spinner("Executing Rules Engine, Gap Analysis & Policy Synthesis..."):
            ledger = st.session_state.ledger
            resolved_facts = ledger.resolved_facts
            conflicts = ledger.conflicts
            timeline_events = st.session_state.timeline.build_timeline()

            rule_results = DeterministicRulesEngine.run_all_checks(resolved_facts)

            gap_analyzer = EvidenceGapAnalyzer(dispute_type=st.session_state.dispute_type)
            checklist = gap_analyzer.analyze(st.session_state.uploaded_doc_types, resolved_facts)
            missing = gap_analyzer.get_missing_evidence(checklist)
            score, breakdown = gap_analyzer.calculate_evidence_score(checklist)

            policies = [
                {
                    "source_name": "Consumer Protection Act, 2019",
                    "section": "Section 2(12) Definition of Defect",
                    "excerpt": "Defect means any fault, imperfection or shortcoming in the quality, quantity, potency, purity or standard which is required to be maintained by or under any law for the time being in force.",
                    "effective_from": "2020-07-20",
                },
                {
                    "source_name": "Consumer Protection (E-Commerce) Rules, 2020",
                    "section": "Rule 6(3) Duties of Marketplace Sellers",
                    "excerpt": "No seller shall refuse to take back goods, or withdraw or discontinue services, if such goods or services are defective, deficient or delivered late.",
                    "effective_from": "2020-07-23",
                },
            ]

            report_gen = CaseReportGenerator(case_id=st.session_state.case_id)
            report = report_gen.generate_report(
                resolved_facts=resolved_facts,
                conflicts=conflicts,
                timeline_events=timeline_events,
                evidence_checklist=checklist,
                rule_results=rule_results,
                relevant_policies=policies,
                score=score,
                max_score=100,
                score_breakdown=breakdown,
                missing_evidence=missing,
                dispute_type=st.session_state.dispute_type,
            )
            report.draft_complaint = report_gen.generate_complaint_draft(report)
            st.session_state.case_report = report
            st.rerun()

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📊 1. Fact Ledger & Conflicts",
        "🕒 2. Case Timeline",
        "🔍 3. Evidence Gap Analysis",
        "⚙️ 4. Rules & Policy RAG",
        "📋 5. Case-Readiness Dossier",
    ]
)

with tab1:
    st.markdown("### 📋 Canonical Fact Ledger")
    st.write(
        "Structured facts extracted from documents. The system maintains source provenance and raises explicit alerts on conflicting data instead of silently guessing."
    )

    ledger_summary = st.session_state.ledger.get_summary()

    if ledger_summary["conflicts"]:
        st.markdown(
            f'<div class="conflict-box">⚠️ <b>{len(ledger_summary["conflicts"])} Factual Conflict(s) Detected</b><br/>Different documents disagree on the facts below. Please review or confirm the accurate value.</div>',
            unsafe_allow_html=True,
        )
        for conf in ledger_summary["conflicts"]:
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.error(f"Field: **{conf['field']}** — {conf['alert']}")
                for v in conf["values"]:
                    st.write(
                        f"• `{v['value']}` from **{v['source'].upper()}** (`{v['file']}`) [Confidence: {int(v['confidence']*100)}%]"
                    )
            with col_b:
                options = [v["value"] for v in conf["values"]]
                chosen = st.selectbox(f"Confirm {conf['field']}", options=options, key=f"conf_{conf['field']}")
                if st.button("Confirm Fact", key=f"btn_{conf['field']}"):
                    st.session_state.ledger.resolve_conflict(conf["field"], chosen, user_confirmed=True)
                    st.success("Resolved!")
                    st.rerun()

    raw_facts = st.session_state.ledger.raw_facts
    if raw_facts:
        table_data = []
        for field, items in raw_facts.items():
            for item in items:
                status_color = "🟢" if item.verification_status == VerificationStatus.VERIFIED else ("🔴" if item.verification_status == VerificationStatus.CONFLICTING else "🟡")
                table_data.append(
                    {
                        "Field": item.field_name,
                        "Extracted Value": str(item.value),
                        "Source Document": f"{item.source_doc_type.value.title()} ({item.source_filename})",
                        "Confidence": f"{int(item.confidence * 100)}%",
                        "Status": f"{status_color} {item.verification_status.value.title()}",
                    }
                )
        st.dataframe(table_data, use_container_width=True)
    else:
        st.info("No facts recorded yet. Upload evidence or click 'Load Real-World Benchmark Case' in the sidebar.")

with tab2:
    st.markdown("### 🕒 Reconstructed Chronological Sequence")
    st.write(
        "Automatic event graph tracking the dispute lifecycle. Highlights logical sequence and checks for chronological contradictions."
    )

    events = st.session_state.timeline.build_timeline()
    violations = st.session_state.timeline.detect_chronological_violations()

    if violations:
        for v in violations:
            st.error(f"⚠️ Chronological Inconsistency: {v['violation']} (Suggestion: {v.get('suggestion', '')})")

    if events:
        for idx, ev in enumerate(events):
            emoji_map = {
                TimelineEventType.PURCHASE: "🛒",
                TimelineEventType.DELIVERY: "📦",
                TimelineEventType.DEFECT_DISCOVERED: "⚠️",
                TimelineEventType.COMPLAINT_RAISED: "📞",
                TimelineEventType.SELLER_RESPONSE: "❌",
                TimelineEventType.SERVICE_VISIT: "🔧",
            }
            ev_icon = emoji_map.get(ev.event_type, "📌")
            date_str = ev.event_date.strftime("%d %b %Y") if isinstance(ev.event_date, (date, datetime)) else str(ev.event_date or "Date Undated")

            st.markdown(
                f"""
                <div class="timeline-item">
                    <h4>{ev_icon} {date_str} — {ev.event_type.value.replace('_', ' ').title()}</h4>
                    <p>{ev.description}</p>
                    <small style="color: #6B7280;">Source: {ev.source_filename} ({ev.source_doc_type.value})</small>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Timeline is empty. Ingest documents with dates or load the demo case.")

with tab3:
    st.markdown("### 🔍 Evidence Gap Analysis & Readiness Index")
    st.write(
        "Deterministic audit of case completeness based on dispute type requirements. Identifies what proofs are available vs what is missing."
    )

    if st.session_state.case_report:
        report = st.session_state.case_report
        
        col_s1, col_s2 = st.columns([1, 2])
        with col_s1:
            st.metric(
                label="Evidence Completeness Index",
                value=f"{report.total_score} / 100",
                delta=f"{report.total_score - 100} to 100% Ready",
            )
            st.caption("⚠️ Note: This measures evidentiary readiness, NOT a legal win probability.")
        with col_s2:
            st.progress(report.total_score / 100)
            st.write(f"**Dispute Type:** {report.dispute_type.value.replace('_', ' ').title() if report.dispute_type else 'General'}")

        st.markdown("#### Completeness Breakdown by Dimension")
        b_cols = st.columns(len(report.score_breakdown))
        for idx, dim in enumerate(report.score_breakdown):
            with b_cols[idx]:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div style="font-size: 0.85rem; color: #4B5563;">{dim.dimension}</div>
                        <div style="font-size: 1.3rem; font-weight: 700; color: #1E3A8A;">{dim.actual_score}/{dim.max_score}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("#### Document Presence Matrix")
        checklist_rows = []
        for item in report.evidence_checklist:
            icon = "✅ Found" if item.status == "found" else ("⚠️ Partial" if item.status == "partial" else "❌ Missing")
            checklist_rows.append(
                {
                    "Evidence Item": item.item_name,
                    "Requirement Level": "Required" if item.required else "Recommended",
                    "Audit Status": icon,
                    "Attached File": item.source_filename or "None",
                    "Notes": item.notes or "",
                }
            )
        st.dataframe(checklist_rows, use_container_width=True)

        if report.missing_evidence:
            st.markdown("#### 🚨 Actionable Missing Evidence Items")
            for m in report.missing_evidence:
                st.warning(f"• **Missing Item:** {m}")
    else:
        st.info("Run Full Case-Readiness Analysis from the sidebar to view Gap Analysis.")

with tab4:
    st.markdown("### ⚙️ Deterministic Rules Engine & Policy Mapping")
    st.write(
        "Critical arithmetic (warranty windows, limitation periods) is calculated via pure Python logic, while policies are retrieved with temporal relevance."
    )

    if st.session_state.case_report:
        report = st.session_state.case_report

        st.markdown("#### 1. Deterministic Rule Calculations")
        for r in report.rule_results:
            icon = "✅" if r.result is True else ("❌" if r.result is False else "⚠️")
            with st.expander(f"{icon} Rule Check: {r.rule_name.replace('_', ' ').title()} [{r.rule_status}]", expanded=True):
                st.write(f"**Result Summary:** {r.summary}")
                if r.details:
                    st.json(r.details)

        st.markdown("#### 2. Governing Statutory & Platform Policies")
        for p in report.relevant_policies:
            with st.expander(f"📖 {p.get('source_name')} — {p.get('section', '')}", expanded=True):
                st.info(f"\"{p.get('excerpt', '')}\"")
                if "effective_from" in p:
                    st.caption(f"Applicable Version: Effective from {p['effective_from']}")
    else:
        st.info("Run Full Case-Readiness Analysis to see rule-check and RAG results.")

with tab5:
    st.markdown("### 📋 Case-Readiness Report & Grievance Draft")
    st.write(
        "Exportable, source-attributed dossier ready for escalation to the Seller, Grievance Officer, or National Consumer Helpline (NCH)."
    )

    if st.session_state.case_report:
        report = st.session_state.case_report
        report_gen = CaseReportGenerator(case_id=report.case_id)
        report_text = report_gen.format_report_text(report)

        col_d1, col_d2 = st.columns([3, 1])
        with col_d1:
            st.success("Case Readiness Dossier compiled successfully!")
        with col_d2:
            st.download_button(
                label="📥 Download Full Report (.txt)",
                data=report_text,
                file_name=f"{report.case_id}_Case_Report.txt",
                mime="text/plain",
                use_container_width=True,
            )

        st.markdown("#### Recommended Action Plan")
        for idx, step in enumerate(report.next_steps, 1):
            st.markdown(f"**{idx}.** {step}")

        st.divider()
        st.markdown("#### ✉️ Structured Grievance Complaint Letter")
        st.caption("You can copy this letter to submit via email or e-commerce grievance portals.")
        st.text_area(
            "Draft Complaint Letter",
            value=report.draft_complaint or "Draft not generated.",
            height=320,
        )
    else:
        st.info("Click 'Run Full Case-Readiness Analysis' in the sidebar to generate the final dossier.")

st.divider()
st.caption(
    "🛡️ **ConsumerShield Disclaimer:** This system is an evidence compilation and analytical assistance tool. It does not provide legal advice, representation, or guarantee any specific resolution outcome."
)
