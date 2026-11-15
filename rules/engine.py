"""
ConsumerShield — Deterministic Rules Engine
Pure-Python checks for warranty, return-window, and limitation-period rules.
Every check returns a RuleCheckResult with full provenance.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from dateutil.relativedelta import relativedelta

from evidence.schemas import RuleCheckResult


class DeterministicRulesEngine:
    """Static-method collection for deterministic consumer-dispute checks."""


    @staticmethod
    def evaluate_warranty_status(
        purchase_date: Optional[date],
        defect_date: Optional[date],
        warranty_months: Optional[int],
    ) -> RuleCheckResult:
        """Check whether the defect was discovered within the warranty period.

        Args:
            purchase_date: Date the product was purchased.
            defect_date: Date the defect was discovered.
            warranty_months: Warranty duration in months.

        Returns:
            RuleCheckResult with rule_name ``warranty_period_check``.
        """
        missing: List[str] = []
        if purchase_date is None:
            missing.append("purchase date")
        if defect_date is None:
            missing.append("defect date")
        if warranty_months is None:
            missing.append("warranty duration")

        if missing:
            return RuleCheckResult(
                rule_name="warranty_period_check",
                rule_status="FAILED_PRECONDITION",
                result=None,
                summary=f"Cannot evaluate warranty: missing {', '.join(missing)}.",
                details={"missing_fields": missing},
            )

        warranty_end = purchase_date + relativedelta(months=warranty_months)
        within = defect_date <= warranty_end
        delta = (warranty_end - defect_date).days

        if within:
            summary = (
                f"Defect is within warranty. "
                f"{delta} day(s) remaining until warranty expires on {warranty_end.isoformat()}."
            )
        else:
            summary = (
                f"Defect is outside warranty. "
                f"Warranty expired {abs(delta)} day(s) ago on {warranty_end.isoformat()}."
            )

        return RuleCheckResult(
            rule_name="warranty_period_check",
            rule_status="EVALUATED",
            result=within,
            summary=summary,
            details={
                "purchase_date": purchase_date.isoformat(),
                "defect_date": defect_date.isoformat(),
                "warranty_months": warranty_months,
                "warranty_end": warranty_end.isoformat(),
                "days_remaining": delta if within else 0,
                "days_lapsed": 0 if within else abs(delta),
                "days_delta": delta,
            },
        )


    @staticmethod
    def evaluate_return_window(
        delivery_date: Optional[date],
        complaint_date: Optional[date],
        window_days: int = 7,
    ) -> RuleCheckResult:
        """Check whether the complaint was raised within the return window.

        Args:
            delivery_date: Date the product was delivered.
            complaint_date: Date the complaint / return was initiated.
            window_days: Allowed return window in days (default 7).

        Returns:
            RuleCheckResult with rule_name ``return_window_check``.
        """
        missing: List[str] = []
        if delivery_date is None:
            missing.append("delivery_date")
        if complaint_date is None:
            missing.append("complaint_date")

        if missing:
            return RuleCheckResult(
                rule_name="return_window_check",
                rule_status="FAILED_PRECONDITION",
                result=None,
                summary=f"Cannot evaluate return window: missing {', '.join(missing)}.",
                details={"missing_fields": missing},
            )

        window_end = delivery_date + relativedelta(days=window_days)
        within = complaint_date <= window_end
        delta = (window_end - complaint_date).days

        if within:
            summary = (
                f"Complaint is within the {window_days}-day return window. "
                f"{delta} day(s) remaining until window closes on {window_end.isoformat()}."
            )
        else:
            summary = (
                f"Complaint is outside the {window_days}-day return window. "
                f"Window closed {abs(delta)} day(s) ago on {window_end.isoformat()}."
            )

        elapsed = (complaint_date - delivery_date).days
        return RuleCheckResult(
            rule_name="return_window_check",
            rule_status="EVALUATED",
            result=within,
            summary=summary,
            details={
                "delivery_date": delivery_date.isoformat(),
                "complaint_date": complaint_date.isoformat(),
                "window_days": window_days,
                "window_end": window_end.isoformat(),
                "days_remaining": delta if within else 0,
                "days_lapsed": 0 if within else abs(delta),
                "days_elapsed": elapsed,
            },
        )


    @staticmethod
    def evaluate_complaint_timeline(
        purchase_date: Optional[date],
        complaint_date: Optional[date],
        max_years: int = 2,
    ) -> RuleCheckResult:
        """Check whether the complaint was filed within the limitation period.

        Under the Consumer Protection Act, complaints must generally be filed
        within *max_years* years of the cause of action.

        Args:
            purchase_date: Date the product was purchased (cause of action).
            complaint_date: Date the formal complaint was filed.
            max_years: Limitation period in years (default 2).

        Returns:
            RuleCheckResult with rule_name ``complaint_limitation_check``.
        """
        missing: List[str] = []
        if purchase_date is None:
            missing.append("purchase_date")
        if complaint_date is None:
            missing.append("complaint_date")

        if missing:
            return RuleCheckResult(
                rule_name="complaint_limitation_check",
                rule_status="FAILED_PRECONDITION",
                result=None,
                summary=f"Cannot evaluate limitation period: missing {', '.join(missing)}.",
                details={"missing_fields": missing},
            )

        limitation_end = purchase_date + relativedelta(years=max_years)
        within = complaint_date <= limitation_end
        delta = (limitation_end - complaint_date).days

        if within:
            summary = (
                f"Complaint is within the {max_years}-year limitation period. "
                f"{delta} day(s) remaining until limitation expires on {limitation_end.isoformat()}."
            )
        else:
            summary = (
                f"Complaint is outside the {max_years}-year limitation period. "
                f"Limitation expired {abs(delta)} day(s) ago on {limitation_end.isoformat()}."
            )

        return RuleCheckResult(
            rule_name="complaint_limitation_check",
            rule_status="EVALUATED",
            result=within,
            summary=summary,
            details={
                "purchase_date": purchase_date.isoformat(),
                "complaint_date": complaint_date.isoformat(),
                "max_years": max_years,
                "limitation_end": limitation_end.isoformat(),
                "days_remaining": delta if within else 0,
                "days_lapsed": 0 if within else abs(delta),
            },
        )


    @staticmethod
    def run_all_checks(facts: Dict[str, Any]) -> List[RuleCheckResult]:
        """Run every applicable rule check against a resolved-facts dictionary.

        Expected keys (all optional — missing ones yield FAILED_PRECONDITION):
            purchase_date, delivery_date, defect_date, complaint_date,
            warranty_period_months, return_window_days.

        Dates should be ISO-8601 strings (``YYYY-MM-DD``); they are parsed here.

        Args:
            facts: Resolved-facts dict from the evidence pipeline.

        Returns:
            List of RuleCheckResult for every check that was attempted.
        """

        def _parse_date(key: str) -> Optional[date]:
            val = facts.get(key)
            if val is None:
                return None
            if isinstance(val, date):
                return val
            try:
                return date.fromisoformat(str(val))
            except (ValueError, TypeError):
                return None

        purchase_date = _parse_date("purchase_date")
        delivery_date = _parse_date("delivery_date")
        defect_date = _parse_date("defect_date")
        complaint_date = _parse_date("complaint_date")

        warranty_months = facts.get("warranty_period_months")
        if warranty_months is not None:
            try:
                warranty_months = int(warranty_months)
            except (ValueError, TypeError):
                warranty_months = None

        window_days = facts.get("return_window_days", 7)
        try:
            window_days = int(window_days)
        except (ValueError, TypeError):
            window_days = 7

        results: List[RuleCheckResult] = []

        results.append(
            DeterministicRulesEngine.evaluate_warranty_status(
                purchase_date, defect_date, warranty_months
            )
        )

        results.append(
            DeterministicRulesEngine.evaluate_return_window(
                delivery_date, complaint_date, window_days
            )
        )

        results.append(
            DeterministicRulesEngine.evaluate_complaint_timeline(
                purchase_date, complaint_date
            )
        )

        return results
