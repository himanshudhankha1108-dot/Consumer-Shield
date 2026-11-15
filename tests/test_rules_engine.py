"""
Tests for Deterministic Python Rules Engine
"""
from datetime import date
import pytest
from rules.engine import DeterministicRulesEngine


class TestDeterministicRulesEngine:
    def test_within_warranty(self):
        purchase = date(2026, 1, 10)
        defect = date(2026, 2, 15)
        res = DeterministicRulesEngine.evaluate_warranty_status(purchase, defect, warranty_months=12)
        assert res.rule_status == "EVALUATED"
        assert res.result is True
        assert res.details.get("days_delta", 0) > 0

    def test_expired_warranty(self):
        purchase = date(2025, 1, 10)
        defect = date(2026, 2, 15)
        res = DeterministicRulesEngine.evaluate_warranty_status(purchase, defect, warranty_months=12)
        assert res.rule_status == "EVALUATED"
        assert res.result is False
        assert res.details.get("days_delta", 0) < 0

    def test_warranty_edge_exact_day(self):
        purchase = date(2025, 1, 10)
        defect = date(2026, 1, 10)
        res = DeterministicRulesEngine.evaluate_warranty_status(purchase, defect, warranty_months=12)
        assert res.rule_status == "EVALUATED"
        assert res.result is True
        assert res.details.get("days_delta") == 0

    def test_missing_purchase_date_precondition(self):
        res = DeterministicRulesEngine.evaluate_warranty_status(None, date(2026, 1, 10), warranty_months=12)
        assert res.rule_status == "FAILED_PRECONDITION"
        assert "purchase date" in res.summary.lower()

    def test_missing_defect_date_precondition(self):
        res = DeterministicRulesEngine.evaluate_warranty_status(date(2026, 1, 10), None, warranty_months=12)
        assert res.rule_status == "FAILED_PRECONDITION"
        assert "defect date" in res.summary.lower()

    def test_return_window_within(self):
        delivery = date(2026, 2, 1)
        complaint = date(2026, 2, 5)
        res = DeterministicRulesEngine.evaluate_return_window(delivery, complaint, window_days=7)
        assert res.rule_status == "EVALUATED"
        assert res.result is True
        assert res.details.get("days_elapsed") == 4

    def test_return_window_expired(self):
        delivery = date(2026, 2, 1)
        complaint = date(2026, 2, 15)
        res = DeterministicRulesEngine.evaluate_return_window(delivery, complaint, window_days=7)
        assert res.rule_status == "EVALUATED"
        assert res.result is False
        assert res.details.get("days_elapsed") == 14

    def test_complaint_limitation_within(self):
        purchase = date(2025, 1, 1)
        complaint = date(2026, 6, 1)
        res = DeterministicRulesEngine.evaluate_complaint_timeline(purchase, complaint, max_years=2)
        assert res.rule_status == "EVALUATED"
        assert res.result is True

    def test_complaint_limitation_expired(self):
        purchase = date(2023, 1, 1)
        complaint = date(2026, 6, 1)
        res = DeterministicRulesEngine.evaluate_complaint_timeline(purchase, complaint, max_years=2)
        assert res.rule_status == "EVALUATED"
        assert res.result is False

    def test_run_all_checks(self):
        facts = {
            "purchase_date": "2026-01-10",
            "delivery_date": "2026-01-12",
            "defect_date": "2026-02-15",
            "complaint_date": "2026-02-18",
            "warranty_period_months": 12,
        }
        results = DeterministicRulesEngine.run_all_checks(facts)
        assert len(results) >= 2
        rule_names = [r.rule_name for r in results]
        assert "warranty_period_check" in rule_names
