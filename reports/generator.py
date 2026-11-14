"""
ConsumerShield — Case-Readiness Report Generator

Assembles extracted facts, timeline, evidence checklist, rule results,
and score data into a complete CaseReadinessReport, then renders it as
a JSON-serialisable dict, a plain-text summary, or a formal complaint
letter draft.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from evidence.schemas import (
    CaseReadinessReport,
    ConflictAlert,
    DisputeType,
    EvidenceChecklistItem,
    RuleCheckResult,
    ScoreDimension,
    TimelineEvent,
)


class CaseReportGenerator:
    """Builds and formats a CaseReadinessReport for a given case."""

    def __init__(self, case_id: str) -> None:
        self.case_id = case_id

    # ── Core assembly ──────────────────────────────────────────

    def generate_report(
        self,
        resolved_facts: Dict[str, Any],
        conflicts: List[ConflictAlert],
        timeline_events: List[TimelineEvent],
        evidence_checklist: List[EvidenceChecklistItem],
        rule_results: List[RuleCheckResult],
        relevant_policies: List[Dict[str, Any]],
        score: int,
        max_score: int,
        score_breakdown: List[ScoreDimension],
        missing_evidence: List[str],
        dispute_type: Optional[DisputeType] = None,
    ) -> CaseReadinessReport:
        """Assemble all analysis outputs into a single CaseReadinessReport.

        Automatically generates ``next_steps`` recommendations based on
        missing evidence items, failed rule checks, and unresolved
        conflicts.
        """
        next_steps = self._build_next_steps(
            missing_evidence=missing_evidence,
            rule_results=rule_results,
            conflicts=conflicts,
            evidence_checklist=evidence_checklist,
        )

        return CaseReadinessReport(
            case_id=self.case_id,
            generated_at=datetime.utcnow(),
            dispute_type=dispute_type,
            resolved_facts=resolved_facts,
            conflicts=conflicts,
            timeline=timeline_events,
            evidence_checklist=evidence_checklist,
            rule_results=rule_results,
            relevant_policies=relevant_policies,
            total_score=score,
            max_score=max_score,
            score_breakdown=score_breakdown,
            missing_evidence=missing_evidence,
            next_steps=next_steps,
        )

    # ── Next-steps logic ───────────────────────────────────────

    @staticmethod
    def _build_next_steps(
        missing_evidence: List[str],
        rule_results: List[RuleCheckResult],
        conflicts: List[ConflictAlert],
        evidence_checklist: List[EvidenceChecklistItem],
    ) -> List[str]:
        """Derive actionable next-step recommendations.

        Sources:
        1. Missing / partial evidence items → upload prompts.
        2. Failed-precondition rule checks → specific remediation.
        3. Unresolved conflicts → resolution prompts.
        """
        steps: List[str] = []

        # ---- 1. Missing evidence --------------------------------
        # Map checklist item names to friendly upload instructions.
        _UPLOAD_HINTS: Dict[str, str] = {
            "invoice": "Upload the original purchase invoice or receipt showing the transaction date, amount, and seller details",
            "warranty": "Upload warranty card or document specifying warranty duration and terms",
            "defect": "Take dated photographs of the product defect from multiple angles and upload them",
            "photo": "Take dated photographs of the product defect from multiple angles and upload them",
            "complaint": "Upload a copy of your written complaint to the seller (email, WhatsApp screenshot, or letter)",
            "response": "Upload the seller's response or denial communication",
            "denial": "Upload the seller's written denial or rejection of your claim",
            "job sheet": "Upload the service centre job sheet or inspection report",
            "tracking": "Upload the delivery tracking page or screenshot showing delivery status",
            "order": "Upload your order confirmation email or screenshot",
            "payment": "Upload payment proof such as bank statement, UPI screenshot, or credit card statement",
            "return": "Upload evidence of your return request (email, chat, or portal screenshot)",
            "escalation": "Upload evidence of escalation to the platform's grievance officer",
            "rejection": "Upload the written warranty rejection from the brand or service centre",
        }

        for item in evidence_checklist:
            if item.status in ("missing", "partial") and item.required:
                item_lower = item.item_name.lower()
                hint = None
                for keyword, suggestion in _UPLOAD_HINTS.items():
                    if keyword in item_lower:
                        hint = suggestion
                        break
                if hint:
                    steps.append(hint)
                else:
                    steps.append(
                        f"Upload evidence for: {item.item_name}"
                    )

        # ---- 2. Failed rule checks -----------------------------
        for rule in rule_results:
            if rule.rule_status == "FAILED_PRECONDITION":
                # Give specific advice based on rule name patterns
                name_lower = rule.rule_name.lower()
                if "warranty" in name_lower:
                    steps.append(
                        "Upload warranty card or document specifying warranty duration"
                    )
                elif "return" in name_lower or "refund" in name_lower:
                    steps.append(
                        "Upload the return/refund policy document or screenshot from the seller/platform"
                    )
                else:
                    steps.append(
                        f"Provide additional evidence for rule check: {rule.rule_name} — {rule.summary}"
                    )
            elif rule.result is False:
                # Rule was evaluated but failed
                name_lower = rule.rule_name.lower()
                if "warranty" in name_lower:
                    steps.append(
                        "The warranty period appears to have expired. Check if an extended warranty was purchased or if the defect is a manufacturing defect (which may have longer statutory coverage)"
                    )
                elif "return" in name_lower:
                    steps.append(
                        "The return window appears to have passed. Document any exceptional circumstances that delayed your return request"
                    )

        # ---- 3. Unresolved conflicts ----------------------------
        for conflict in conflicts:
            field = conflict.field
            sources = [
                v.get("source", "unknown") for v in conflict.values
            ]
            source_str = " and ".join(dict.fromkeys(sources))  # unique, ordered
            steps.append(
                f"Resolve the conflicting {field} values between your {source_str} documents"
            )

        # De-duplicate while preserving order
        seen: set[str] = set()
        unique_steps: List[str] = []
        for s in steps:
            if s not in seen:
                seen.add(s)
                unique_steps.append(s)

        return unique_steps

    # ── Complaint draft ────────────────────────────────────────

    def generate_complaint_draft(self, report: CaseReadinessReport) -> str:
        """Generate a formal consumer complaint letter template.

        Uses resolved facts from the report to fill in a structured
        letter.  Placeholders are left for the consumer's personal
        details.
        """
        facts = report.resolved_facts
        product = facts.get("product_name", "[Product Name]")
        brand = facts.get("brand", "[Brand]")
        model = facts.get("model_number", "")
        seller = facts.get("seller_name", "[Seller Name]")
        platform = facts.get("platform", "")
        order_id = facts.get("order_id", "[Order ID]")
        purchase_date = facts.get("purchase_date", "[Purchase Date]")
        amount = facts.get("amount_paid", "[Amount]")
        currency = facts.get("currency", "INR")
        defect_desc = facts.get("defect_description", "[Description of defect]")
        defect_date = facts.get("defect_date", "[Defect Date]")
        complaint_date = facts.get("complaint_date", "[Complaint Date]")
        seller_response = facts.get("seller_response", "")
        repair_demanded = facts.get("repair_amount_demanded")
        service_center = facts.get("service_center")

        # Fallback to timeline if purchase_date was not resolved in facts
        if purchase_date == "[Purchase Date]" and report.timeline:
            for evt in report.timeline:
                if evt.event_type == TimelineEventType.PURCHASE and evt.event_date:
                    purchase_date = evt.event_date.isoformat()
                    break

        dispute_label = (
            report.dispute_type.value.replace("_", " ").title()
            if report.dispute_type
            else "Consumer Dispute"
        )

        model_str = f" (Model: {model})" if model else ""
        platform_str = f" via {platform}" if platform else ""

        # Build timeline summary
        timeline_lines: List[str] = []
        for evt in report.timeline:
            date_str = evt.event_date.isoformat() if evt.event_date else "Date unknown"
            timeline_lines.append(f"  - {date_str}: {evt.description}")
        timeline_block = "\n".join(timeline_lines) if timeline_lines else "  [Timeline details]"

        # Attachments list
        attachments: List[str] = []
        for item in report.evidence_checklist:
            if item.status == "found" and item.source_filename:
                attachments.append(f"  - {item.item_name} ({item.source_filename})")
            elif item.status == "found":
                attachments.append(f"  - {item.item_name}")
        attachment_block = "\n".join(attachments) if attachments else "  [List of enclosed documents]"

        # Service center quotation paragraph
        repair_quote_para = ""
        if repair_demanded:
            repair_quote_para = (
                f"\nFurthermore, the service partner ({service_center or 'Authorized Service Center'}) "
                f"unlawfully rejected free warranty coverage and demanded payment of {currency} {repair_demanded} "
                f"for repairs, in clear violation of the terms of warranty and Section 2(47) of the Consumer Protection Act, 2019.\n"
            )

        # Seller response context
        response_para = ""
        if seller_response:
            resp_lower = seller_response.lower()
            is_rejection = any(w in resp_lower for w in ["reject", "denied", "refus", "no refund", "payment", "exclude", "unlawful"])
            if is_rejection:
                response_para = (
                    f"\nThe seller/service provider responded as follows: \"{seller_response}\". "
                    f"This rejection is arbitrary and fails to honor consumer statutory protections.\n"
                )
            else:
                response_para = (
                    f"\nThe seller/service provider responded as follows: \"{seller_response}\". "
                    f"This response is inadequate and does not resolve the core grievance.\n"
                )

        letter = f"""CONSUMER COMPLAINT

Subject: Formal Complaint Regarding {dispute_label} — {product}{model_str}

Date: {datetime.utcnow().strftime('%d %B %Y')}

To:
  {seller}{platform_str}
  [Seller/Company Address]

From:
  [Your Full Name]
  [Your Address]
  [City, State, PIN Code]
  [Email Address]
  [Phone Number]

Dear Sir/Madam,

I am writing to formally register my complaint regarding the {product}{model_str} manufactured by {brand}, purchased from {seller}{platform_str} on {purchase_date} (Order ID: {order_id}) for {currency} {amount}.

STATEMENT OF FACTS:

On {purchase_date}, I purchased the above-mentioned product. {f"On {defect_date}, I discovered the following issue: {defect_desc}." if defect_date != "[Defect Date]" else f"I discovered the following issue: {defect_desc}."}
{response_para}{repair_quote_para}
CHRONOLOGY OF EVENTS:

{timeline_block}

RELIEF SOUGHT:

Based on the above facts and applicable consumer protection laws, I request the following:
  1. {"Free-of-cost warranty repair or replacement without demanding payment of " + str(currency) + " " + str(repair_demanded) + ", OR " if repair_demanded else ""}Full refund of {currency} {amount}, OR
  2. Replacement of the defective product with a new unit of the same or equivalent specification, AND
  3. Compensation for the inconvenience, mental agony, and time spent pursuing this matter.

I have previously raised this complaint on {complaint_date} but have not received a satisfactory resolution.

I request you to resolve this matter within 15 days of receipt of this letter, failing which I shall be constrained to approach the appropriate Consumer Disputes Redressal Commission for relief.

ENCLOSED DOCUMENTS:

{attachment_block}

Yours faithfully,

[Your Full Name]
[Your Signature]
"""
        return letter.strip()

    # ── Serialisation ──────────────────────────────────────────

    @staticmethod
    def report_to_dict(report: CaseReadinessReport) -> Dict[str, Any]:
        """Serialise a CaseReadinessReport to a JSON-compatible dict."""
        return report.model_dump(mode="json")

    # ── Plain-text rendering ───────────────────────────────────

    @staticmethod
    def format_report_text(report: CaseReadinessReport) -> str:
        """Render the full report as clean plain text for terminal/PDF."""
        lines: List[str] = []
        sep = "=" * 60

        lines.append(sep)
        lines.append("  CONSUMERSHIELD — CASE READINESS REPORT")
        lines.append(sep)
        lines.append(f"Case ID      : {report.case_id}")
        lines.append(f"Generated    : {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if report.dispute_type:
            lines.append(f"Dispute Type : {report.dispute_type.value.replace('_', ' ').title()}")
        lines.append("")

        # ── Score summary ──
        lines.append(f"OVERALL SCORE: {report.total_score} / {report.max_score}")
        lines.append("-" * 40)
        for dim in report.score_breakdown:
            bar_len = 20
            filled = round(dim.actual_score / dim.max_score * bar_len) if dim.max_score else 0
            bar = "█" * filled + "░" * (bar_len - filled)
            lines.append(
                f"  {dim.dimension:<30} {dim.actual_score:>3}/{dim.max_score:<3}  [{bar}]"
            )
            lines.append(f"    {dim.details}")
        lines.append("")

        # ── Resolved facts ──
        lines.append("RESOLVED FACTS")
        lines.append("-" * 40)
        if report.resolved_facts:
            for key, val in report.resolved_facts.items():
                lines.append(f"  {key:<30}: {val}")
        else:
            lines.append("  No facts resolved yet.")
        lines.append("")

        # ── Conflicts ──
        if report.conflicts:
            lines.append("⚠  CONFLICTS DETECTED")
            lines.append("-" * 40)
            for c in report.conflicts:
                lines.append(f"  Field: {c.field}")
                lines.append(f"  Alert: {c.alert}")
                for v in c.values:
                    lines.append(
                        f"    • {v.get('source', '?')}: {v.get('value', '?')} "
                        f"(confidence: {v.get('confidence', '?')})"
                    )
            lines.append("")

        # ── Timeline ──
        lines.append("CASE TIMELINE")
        lines.append("-" * 40)
        if report.timeline:
            for evt in report.timeline:
                date_str = (
                    evt.event_date.isoformat() if evt.event_date else "  ????-??-??"
                )
                lines.append(f"  {date_str}  [{evt.event_type.value}]  {evt.description}")
        else:
            lines.append("  No timeline events recorded.")
        lines.append("")

        # ── Evidence checklist ──
        lines.append("EVIDENCE CHECKLIST")
        lines.append("-" * 40)
        for item in report.evidence_checklist:
            icon = {"found": "✅", "partial": "⚠️", "missing": "❌"}.get(
                item.status, "?"
            )
            req = "Req" if item.required else "Opt"
            lines.append(f"  {icon} {item.item_name:<35} [{req}]  {item.status}")
            if item.notes:
                lines.append(f"       {item.notes}")
        lines.append("")

        # ── Rule results ──
        lines.append("RULE CHECK RESULTS")
        lines.append("-" * 40)
        if report.rule_results:
            for rule in report.rule_results:
                if rule.rule_status == "FAILED_PRECONDITION":
                    icon = "⚠️"
                elif rule.result is True:
                    icon = "✅"
                elif rule.result is False:
                    icon = "❌"
                else:
                    icon = "—"
                lines.append(f"  {icon} {rule.rule_name}: {rule.summary}")
        else:
            lines.append("  No rules evaluated.")
        lines.append("")

        # ── Relevant policies ──
        if report.relevant_policies:
            lines.append("RELEVANT POLICIES")
            lines.append("-" * 40)
            for pol in report.relevant_policies:
                lines.append(f"  • {pol.get('source', 'Unknown')}: {pol.get('text', '')[:120]}...")
            lines.append("")

        # ── Missing evidence ──
        if report.missing_evidence:
            lines.append("MISSING EVIDENCE")
            lines.append("-" * 40)
            for item in report.missing_evidence:
                lines.append(f"  • {item}")
            lines.append("")

        # ── Next steps ──
        if report.next_steps:
            lines.append("RECOMMENDED NEXT STEPS")
            lines.append("-" * 40)
            for i, step in enumerate(report.next_steps, 1):
                lines.append(f"  {i}. {step}")
            lines.append("")

        lines.append(sep)
        lines.append("  Disclaimer: ConsumerShield is an evidence organization")
        lines.append("  tool. It does not provide legal advice or guarantee")
        lines.append("  dispute outcomes.")
        lines.append(sep)

        return "\n".join(lines)
