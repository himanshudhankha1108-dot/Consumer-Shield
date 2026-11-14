"""
End-to-End Pipeline Integration Test
Simulates complete flow: Ingestion -> Fact Extraction -> Canonical Ledger -> Timeline -> Rules -> Gap Analysis -> Report Dossier
"""
from datetime import date
import pytest

from evidence.schemas import (
    CaseExtractionOutput,
    DisputeType,
    DocumentType,
    TimelineEventType,
)
from evidence.ledger import CanonicalFactLedger
from evidence.timeline import CaseTimeline
from evidence.gap_analyzer import EvidenceGapAnalyzer
from rules.engine import DeterministicRulesEngine
from reports.generator import CaseReportGenerator
from ingestion.extractor import extraction_to_fact_items


class TestEndToEndPipeline:
    def test_full_pipeline_synthetic_journey(self):
        # 1. Initialize core case engines
        ledger = CanonicalFactLedger()
        timeline = CaseTimeline()
        dispute_type = DisputeType.DEFECTIVE_PRODUCT

        # 2. Simulate extraction from Invoice
        invoice_ext = CaseExtractionOutput(
            product_name="Sony WH-1000XM4 Headphones",
            seller_name="Appario Retail",
            purchase_date="2026-01-10",
            amount_paid=19990.0,
            raw_evidence_quotes=["Invoice dated 10 Jan 2026", "Total Rs 19,990"],
        )
        invoice_facts = extraction_to_fact_items(invoice_ext, DocumentType.INVOICE, "Invoice_Sony.pdf")
        for f in invoice_facts:
            ledger.record_fact(f)

        # 3. Simulate extraction from Warranty Card
        warranty_ext = CaseExtractionOutput(
            warranty_period_months=12,
            warranty_type="Manufacturer Comprehensive",
            raw_evidence_quotes=["1 Year Limited Warranty"],
        )
        warranty_facts = extraction_to_fact_items(warranty_ext, DocumentType.WARRANTY_CARD, "Sony_Warranty.pdf")
        for f in warranty_facts:
            ledger.record_fact(f)

        # 4. Simulate customer complaint email with conflicting purchase date
        email_ext = CaseExtractionOutput(
            purchase_date="2026-01-14",  # Intentional conflict with invoice
            defect_date="2026-02-15",
            defect_description="ANC crackling noise and battery charging failure",
            seller_response="Claim rejected due to customer physical inspection clause",
            raw_evidence_quotes=["Customer email dated 16 Feb 2026"],
        )
        email_facts = extraction_to_fact_items(email_ext, DocumentType.EMAIL, "Complaint_Thread.txt")
        for f in email_facts:
            ledger.record_fact(f)

        # Verify conflict was caught by ledger
        summary = ledger.get_summary()
        assert len(summary["conflicts"]) == 1
        assert summary["conflicts"][0]["field"] == "purchase_date"

        # User resolves conflict choosing the official invoice date
        ledger.resolve_conflict("purchase_date", "2026-01-10", user_confirmed=True)
        assert len(ledger.conflicts) == 0
        resolved_facts = ledger.resolved_facts

        # 5. Populate timeline
        from evidence.schemas import TimelineEvent
        timeline.add_event(
            TimelineEvent(
                event_type=TimelineEventType.PURCHASE,
                event_date=date(2026, 1, 10),
                description="Product purchased from Appario Retail",
                source_doc_type=DocumentType.INVOICE,
                source_filename="Invoice_Sony.pdf",
            )
        )
        timeline.add_event(
            TimelineEvent(
                event_type=TimelineEventType.DEFECT_DISCOVERED,
                event_date=date(2026, 2, 15),
                description="ANC crackling noise identified",
                source_doc_type=DocumentType.EMAIL,
                source_filename="Complaint_Thread.txt",
            )
        )
        timeline.add_event(
            TimelineEvent(
                event_type=TimelineEventType.SELLER_RESPONSE,
                event_date=date(2026, 2, 18),
                description="Seller rejected warranty claim",
                source_doc_type=DocumentType.EMAIL,
                source_filename="Complaint_Thread.txt",
            )
        )

        timeline_events = timeline.build_timeline()
        assert len(timeline_events) >= 3

        # 6. Execute Deterministic Rules Engine
        rule_results = DeterministicRulesEngine.run_all_checks(resolved_facts)
        warranty_result = next((r for r in rule_results if r.rule_name == "warranty_period_check"), None)
        assert warranty_result is not None
        assert warranty_result.rule_status == "EVALUATED"
        assert warranty_result.result is True  # 15 Feb is within 12 months of 10 Jan

        # 7. Execute Evidence Gap Analysis (Notice: No DEFECT_PHOTO was uploaded!)
        uploaded_doc_types = [DocumentType.INVOICE, DocumentType.WARRANTY_CARD, DocumentType.EMAIL]
        gap_analyzer = EvidenceGapAnalyzer(dispute_type=dispute_type)
        checklist = gap_analyzer.analyze(uploaded_doc_types, resolved_facts)
        missing_evidence = gap_analyzer.get_missing_evidence(checklist)
        score, score_breakdown = gap_analyzer.calculate_evidence_score(checklist)

        # Score must be penalized for missing defect photos
        assert score < 100
        assert any("photo" in m.lower() or "defect" in m.lower() for m in missing_evidence)

        # 8. Generate Case-Readiness Dossier
        report_gen = CaseReportGenerator(case_id="CS-TEST-001")
        report = report_gen.generate_report(
            resolved_facts=resolved_facts,
            conflicts=[],
            timeline_events=timeline_events,
            evidence_checklist=checklist,
            rule_results=rule_results,
            relevant_policies=[
                {
                    "source_name": "Consumer Protection Act, 2019",
                    "section": "Section 2(12) Defect",
                    "excerpt": "Any fault or imperfection in quality required to be maintained",
                }
            ],
            score=score,
            max_score=100,
            score_breakdown=score_breakdown,
            missing_evidence=missing_evidence,
            dispute_type=dispute_type,
        )
        draft = report_gen.generate_complaint_draft(report)

        # 9. Verify Dossier Integrity
        assert report.total_score == score
        assert len(report.next_steps) > 0
        assert "Appario Retail" in draft or "Sony" in draft or "10 Jan 2026" in draft or "2026-01-10" in draft
