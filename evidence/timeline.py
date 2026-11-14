"""
ConsumerShield — Chronological Timeline Builder & Contradiction Detector

Collects dated case events, sorts them into a chronological timeline,
and detects logical-ordering violations (e.g. delivery before purchase).
"""
from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from evidence.schemas import DocumentType, TimelineEvent, TimelineEventType


# Document authority priority (lower rank = higher legal authority)
_DOC_PRIORITY: Dict[DocumentType, int] = {
    DocumentType.INVOICE: 1,
    DocumentType.JOB_SHEET: 2,
    DocumentType.WARRANTY_CARD: 3,
    DocumentType.EMAIL: 4,
    DocumentType.WHATSAPP: 5,
    DocumentType.DEFECT_PHOTO: 6,
    DocumentType.USER_STATEMENT: 7,
    DocumentType.RETURN_POLICY: 8,
    DocumentType.OTHER: 9,
}

# Pairs of (earlier_type, later_type) that define the expected logical order.
_EXPECTED_ORDER: List[tuple[TimelineEventType, TimelineEventType]] = [
    (TimelineEventType.PURCHASE, TimelineEventType.DELIVERY),
    (TimelineEventType.DELIVERY, TimelineEventType.DEFECT_DISCOVERED),
    (TimelineEventType.DEFECT_DISCOVERED, TimelineEventType.COMPLAINT_RAISED),
    (TimelineEventType.COMPLAINT_RAISED, TimelineEventType.SELLER_RESPONSE),
]


class CaseTimeline:
    """Maintains a list of ``TimelineEvent`` objects for a consumer case.

    Events can be added in any order; call :meth:`build_timeline` to obtain
    a chronologically sorted list or :meth:`detect_chronological_violations`
    to find logical-ordering anomalies.
    """

    def __init__(self) -> None:
        self._events: List[TimelineEvent] = []

    # ── Mutators ───────────────────────────────────────────────

    def add_event(self, event: TimelineEvent) -> None:
        """Append a ``TimelineEvent`` to the internal list."""
        if event is not None:
            self._events.append(event)

    # ── Timeline construction ──────────────────────────────────

    def build_timeline(self) -> List[TimelineEvent]:
        """Return events sorted by ``event_date`` (ascending), deduplicating redundant milestones.

        Events without a date are placed at the end.
        """
        def _sort_key(e: TimelineEvent) -> tuple[int, date]:
            if e.event_date is None:
                # Undated events sort last.
                return (1, date.max)
            return (0, e.event_date)

        sorted_events = sorted(self._events, key=_sort_key)

        # Deduplicate redundant events occurring on the same date with the same event type
        deduped: List[TimelineEvent] = []
        for evt in sorted_events:
            dup_idx = -1
            for idx, existing in enumerate(deduped):
                if evt.event_type == existing.event_type and evt.event_date == existing.event_date:
                    dup_idx = idx
                    break

            if dup_idx >= 0:
                # Compare source authority and description detail
                existing = deduped[dup_idx]
                r_new = _DOC_PRIORITY.get(evt.source_doc_type, 99) if evt.source_doc_type else 99
                r_old = _DOC_PRIORITY.get(existing.source_doc_type, 99) if existing.source_doc_type else 99
                # If new is from more authoritative document, or has more detailed description at same priority
                if r_new < r_old or (r_new == r_old and len(evt.description) > len(existing.description)):
                    deduped[dup_idx] = evt
            else:
                deduped.append(evt)

        return deduped

    # ── Violation detection ────────────────────────────────────

    def detect_chronological_violations(self) -> List[Dict[str, str]]:
        """Check logical ordering constraints and return violations.

        For each ``(earlier_type, later_type)`` pair in the expected order,
        the detector verifies that every event of *earlier_type* has a date
        ≤ every event of *later_type*.  Violations are returned as dicts:

        .. code-block:: python

            {
                "violation": "<description>",
                "event1": "<earlier event summary>",
                "event2": "<later event summary>",
                "suggestion": "<human-readable advice>",
            }
        """
        violations: List[Dict[str, str]] = []

        # Index dated events by type.
        by_type: Dict[TimelineEventType, List[TimelineEvent]] = {}
        for e in self._events:
            if e.event_date is not None:
                by_type.setdefault(e.event_type, []).append(e)

        for earlier_type, later_type in _EXPECTED_ORDER:
            earlier_events = by_type.get(earlier_type, [])
            later_events = by_type.get(later_type, [])
            if not earlier_events or not later_events:
                continue

            for e_early in earlier_events:
                for e_later in later_events:
                    # Both are guaranteed to have a date (filtered above).
                    assert e_early.event_date is not None
                    assert e_later.event_date is not None
                    if e_early.event_date > e_later.event_date:
                        violations.append(
                            {
                                "violation": (
                                    f"{earlier_type.value} ({e_early.event_date}) "
                                    f"occurs after {later_type.value} "
                                    f"({e_later.event_date})"
                                ),
                                "event1": (
                                    f"{earlier_type.value} on {e_early.event_date} "
                                    f"— {e_early.description}"
                                ),
                                "event2": (
                                    f"{later_type.value} on {e_later.event_date} "
                                    f"— {e_later.description}"
                                ),
                                "suggestion": (
                                    f"Please verify the dates: "
                                    f"{earlier_type.value} should occur before "
                                    f"{later_type.value}. Check the source "
                                    f"documents for potential OCR or extraction "
                                    f"errors."
                                ),
                            }
                        )

        return violations

    # ── Display ────────────────────────────────────────────────

    def get_timeline_display(self) -> List[Dict[str, Optional[str]]]:
        """Return a UI-friendly list of timeline entries.

        Each dict contains:

        * ``date`` — ISO-formatted date string or ``None``
        * ``event_type`` — the ``TimelineEventType`` value
        * ``description`` — free-text event description
        * ``source`` — originating document type
        """
        sorted_events = self.build_timeline()
        return [
            {
                "date": e.event_date.isoformat() if e.event_date else None,
                "event_type": e.event_type.value,
                "description": e.description,
                "source": e.source_doc_type.value,
            }
            for e in sorted_events
        ]
