"""
Tests for Evidence Gap Analysis & Completeness Scorecard
"""
import pytest
from evidence.schemas import DisputeType, DocumentType
from evidence.gap_analyzer import EvidenceGapAnalyzer


class TestEvidenceGapAnalyzer:
    def test_defective_product_complete_evidence(self):
        analyzer = EvidenceGapAnalyzer(dispute_type=DisputeType.DEFECTIVE_PRODUCT)
        uploaded = [
            DocumentType.INVOICE,
            DocumentType.WARRANTY_CARD,
            DocumentType.DEFECT_PHOTO,
            DocumentType.EMAIL,
            DocumentType.JOB_SHEET,
        ]
        facts = {
            "purchase_date": "2026-01-10",
            "defect_date": "2026-02-15",
            "warranty_period_months": 12,
        }
        checklist = analyzer.analyze(uploaded, facts)
        missing = analyzer.get_missing_evidence(checklist)
        score, breakdown = analyzer.calculate_evidence_score(checklist)

        assert score >= 85
        assert len(breakdown) == 5

    def test_defective_product_missing_photo(self):
        analyzer = EvidenceGapAnalyzer(dispute_type=DisputeType.DEFECTIVE_PRODUCT)
        uploaded = [
            DocumentType.INVOICE,
            DocumentType.WARRANTY_CARD,
        ]
        facts = {
            "purchase_date": "2026-01-10",
            "warranty_period_months": 12,
        }
        checklist = analyzer.analyze(uploaded, facts)
        missing = analyzer.get_missing_evidence(checklist)
        score, _ = analyzer.calculate_evidence_score(checklist)

        photo_items = [i for i in checklist if "photo" in i.item_name.lower() or "defect" in i.item_name.lower()]
        assert any(p.status == "missing" for p in photo_items)
        assert score < 80

    def test_denied_refund_gaps(self):
        analyzer = EvidenceGapAnalyzer(dispute_type=DisputeType.DENIED_REFUND)
        uploaded = [DocumentType.INVOICE]
        checklist = analyzer.analyze(uploaded, facts={})
        missing = analyzer.get_missing_evidence(checklist)
        assert len(missing) >= 2
