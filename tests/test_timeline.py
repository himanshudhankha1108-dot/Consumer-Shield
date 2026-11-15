"""
Tests for Case Timeline Builder & Chronological Contradiction Detector
"""
from datetime import date
import pytest
from evidence.schemas import TimelineEvent, TimelineEventType, DocumentType
from evidence.timeline import CaseTimeline


class TestTimeline:
    def test_add_and_sort_events(self):
        timeline = CaseTimeline()
        timeline.add_event(
            TimelineEvent(
                event_type=TimelineEventType.COMPLAINT_RAISED,
                event_date=date(2026, 2, 20),
                description="Raised grievance with brand",
                source_doc_type=DocumentType.EMAIL,
                source_filename="complaint.eml",
            )
        )
        timeline.add_event(
            TimelineEvent(
                event_type=TimelineEventType.PURCHASE,
                event_date=date(2026, 1, 10),
                description="Ordered product",
                source_doc_type=DocumentType.INVOICE,
                source_filename="invoice.pdf",
            )
        )
        timeline.add_event(
            TimelineEvent(
                event_type=TimelineEventType.DELIVERY,
                event_date=date(2026, 1, 14),
                description="Order delivered",
                source_doc_type=DocumentType.INVOICE,
                source_filename="invoice.pdf",
            )
        )

        sorted_events = timeline.build_timeline()
        assert len(sorted_events) == 3
        assert sorted_events[0].event_type == TimelineEventType.PURCHASE
        assert sorted_events[1].event_type == TimelineEventType.DELIVERY
        assert sorted_events[2].event_type == TimelineEventType.COMPLAINT_RAISED

    def test_chronological_violation_detection(self):
        timeline = CaseTimeline()
        timeline.add_event(
            TimelineEvent(
                event_type=TimelineEventType.PURCHASE,
                event_date=date(2026, 1, 20),
                description="Invoice purchase date",
                source_doc_type=DocumentType.INVOICE,
                source_filename="invoice.pdf",
            )
        )
        timeline.add_event(
            TimelineEvent(
                event_type=TimelineEventType.DELIVERY,
                event_date=date(2026, 1, 10),
                description="Claimed delivery date",
                source_doc_type=DocumentType.EMAIL,
                source_filename="claim.txt",
            )
        )

        violations = timeline.detect_chronological_violations()
        assert len(violations) >= 1
        assert "purchase" in violations[0]["violation"].lower() or "delivery" in violations[0]["violation"].lower()

    def test_no_violations_valid_timeline(self):
        timeline = CaseTimeline()
        timeline.add_event(
            TimelineEvent(
                event_type=TimelineEventType.PURCHASE,
                event_date=date(2026, 1, 10),
                description="Purchase",
                source_doc_type=DocumentType.INVOICE,
                source_filename="invoice.pdf",
            )
        )
        timeline.add_event(
            TimelineEvent(
                event_type=TimelineEventType.DELIVERY,
                event_date=date(2026, 1, 13),
                description="Delivery",
                source_doc_type=DocumentType.INVOICE,
                source_filename="invoice.pdf",
            )
        )
        timeline.add_event(
            TimelineEvent(
                event_type=TimelineEventType.DEFECT_DISCOVERED,
                event_date=date(2026, 1, 20),
                description="Defect",
                source_doc_type=DocumentType.WHATSAPP,
                source_filename="chat.txt",
            )
        )
        violations = timeline.detect_chronological_violations()
        assert len(violations) == 0

    def test_timeline_deduplicates_same_date_milestones(self):
        timeline = CaseTimeline()
        timeline.add_event(
            TimelineEvent(
                event_type=TimelineEventType.PURCHASE,
                event_date=date(2026, 1, 5),
                description="Purchased Asus ROG Zephyrus G14 from Croma",
                source_doc_type=DocumentType.INVOICE,
                source_filename="01_invoice.txt",
            )
        )
        timeline.add_event(
            TimelineEvent(
                event_type=TimelineEventType.PURCHASE,
                event_date=date(2026, 1, 5),
                description="Purchased ROG Zephyrus G14 from seller",
                source_doc_type=DocumentType.WHATSAPP,
                source_filename="03_chat.txt",
            )
        )
        events = timeline.build_timeline()
        assert len(events) == 1
        assert "Croma" in events[0].description
        assert events[0].source_doc_type == DocumentType.INVOICE
