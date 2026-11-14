"""
Tests for Canonical Fact Ledger & Conflict Detection
"""
import pytest
from evidence.schemas import FactItem, DocumentType, VerificationStatus
from evidence.ledger import CanonicalFactLedger


class TestCanonicalFactLedger:
    def test_single_fact_recorded(self):
        ledger = CanonicalFactLedger()
        fact = FactItem(
            field_name="purchase_date",
            value="2026-01-10",
            source_doc_type=DocumentType.INVOICE,
            source_filename="invoice.pdf",
            confidence=0.98,
        )
        ledger.record_fact(fact)
        assert ledger.get_resolved_value("purchase_date") == "2026-01-10"
        assert len(ledger.conflicts) == 0

    def test_multiple_sources_same_value(self):
        ledger = CanonicalFactLedger()
        f1 = FactItem(
            field_name="purchase_date",
            value="2026-01-10",
            source_doc_type=DocumentType.INVOICE,
            source_filename="invoice.pdf",
            confidence=0.95,
        )
        f2 = FactItem(
            field_name="purchase_date",
            value="2026-01-10",
            source_doc_type=DocumentType.WARRANTY_CARD,
            source_filename="warranty.pdf",
            confidence=0.90,
        )
        ledger.record_fact(f1)
        ledger.record_fact(f2)

        summary = ledger.get_summary()
        assert len(summary["conflicts"]) == 0
        assert ledger.get_resolved_value("purchase_date") == "2026-01-10"
        # Status upgraded to VERIFIED
        assert ledger.raw_facts["purchase_date"][0].verification_status == VerificationStatus.VERIFIED

    def test_conflict_detection(self):
        ledger = CanonicalFactLedger()
        f1 = FactItem(
            field_name="purchase_date",
            value="2026-01-10",
            source_doc_type=DocumentType.INVOICE,
            source_filename="invoice.pdf",
            confidence=0.98,
        )
        f2 = FactItem(
            field_name="purchase_date",
            value="2026-01-18",
            source_doc_type=DocumentType.EMAIL,
            source_filename="support_email.txt",
            confidence=0.85,
        )
        ledger.record_fact(f1)
        ledger.record_fact(f2)

        summary = ledger.get_summary()
        assert len(summary["conflicts"]) == 1
        assert summary["conflicts"][0]["field"] == "purchase_date"
        assert ledger.raw_facts["purchase_date"][0].verification_status == VerificationStatus.CONFLICTING
        assert ledger.raw_facts["purchase_date"][1].verification_status == VerificationStatus.CONFLICTING

    def test_resolve_conflict_user_confirmation(self):
        ledger = CanonicalFactLedger()
        f1 = FactItem(
            field_name="purchase_date",
            value="2026-01-10",
            source_doc_type=DocumentType.INVOICE,
            source_filename="invoice.pdf",
            confidence=0.98,
        )
        f2 = FactItem(
            field_name="purchase_date",
            value="2026-01-18",
            source_doc_type=DocumentType.EMAIL,
            source_filename="support_email.txt",
            confidence=0.85,
        )
        ledger.record_fact(f1)
        ledger.record_fact(f2)

        resolved = ledger.resolve_conflict("purchase_date", "2026-01-10", user_confirmed=True)
        assert resolved is True
        assert ledger.get_resolved_value("purchase_date") == "2026-01-10"
        assert len(ledger.conflicts) == 0

    def test_summary_counts(self):
        ledger = CanonicalFactLedger()
        ledger.record_fact(
            FactItem(
                field_name="product_name",
                value="Wireless Earbuds",
                source_doc_type=DocumentType.INVOICE,
                source_filename="bill.pdf",
            )
        )
        ledger.record_fact(
            FactItem(
                field_name="amount_paid",
                value=2499.0,
                source_doc_type=DocumentType.INVOICE,
                source_filename="bill.pdf",
            )
        )
        summary = ledger.get_summary()
        assert summary["raw_facts_count"] == 2
        assert len(summary["resolved_facts"]) == 2

    def test_canonical_records_consolidation(self):
        ledger = CanonicalFactLedger()
        # Same product mentioned across invoice and warranty
        ledger.record_fact(
            FactItem(
                field_name="product_name",
                value="Asus ROG Zephyrus G14 Gaming Laptop",
                source_doc_type=DocumentType.INVOICE,
                source_filename="01_invoice.txt",
                confidence=0.98,
            )
        )
        ledger.record_fact(
            FactItem(
                field_name="product_name",
                value="ROG Zephyrus G14",
                source_doc_type=DocumentType.WHATSAPP,
                source_filename="03_chat.txt",
                confidence=0.95,
            )
        )
        records = ledger.canonical_records
        assert len(records) == 1
        assert records[0]["field"] == "product_name"
        assert records[0]["sources_count"] == 2
        assert records[0]["status"] == "verified"
        assert "Asus ROG Zephyrus G14 Gaming Laptop" in records[0]["value"]
