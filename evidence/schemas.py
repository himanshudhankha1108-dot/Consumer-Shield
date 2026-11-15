"""
ConsumerShield — Evidence Data Schemas
Pydantic models for structured facts, case data, and the canonical fact ledger.
Every extracted field carries source provenance and confidence.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    INVOICE = "invoice"
    WARRANTY_CARD = "warranty_card"
    DEFECT_PHOTO = "defect_photo"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    JOB_SHEET = "job_sheet"
    USER_STATEMENT = "user_statement"
    RETURN_POLICY = "return_policy"
    OTHER = "other"


class VerificationStatus(str, Enum):
    EXTRACTED = "extracted"
    VERIFIED = "verified"
    CONFLICTING = "conflicting"
    USER_CONFIRMED = "user_confirmed"
    MISSING = "missing"


class DisputeType(str, Enum):
    DEFECTIVE_PRODUCT = "defective_product"
    DENIED_REFUND = "denied_refund"
    WARRANTY_REJECTION = "warranty_rejection"
    NON_DELIVERY = "non_delivery"
    SHORT_DELIVERY = "short_delivery"
    WRONG_PRODUCT = "wrong_product"
    SERVICE_DEFICIENCY = "service_deficiency"
    OTHER = "other"


class TimelineEventType(str, Enum):
    PURCHASE = "purchase"
    DELIVERY = "delivery"
    DEFECT_DISCOVERED = "defect_discovered"
    COMPLAINT_RAISED = "complaint_raised"
    SELLER_RESPONSE = "seller_response"
    ESCALATION = "escalation"
    SERVICE_VISIT = "service_visit"
    REPLACEMENT_REFUND = "replacement_refund"
    OTHER = "other"


class FactItem(BaseModel):
    """A single extracted fact with full source provenance."""
    field_name: str
    value: Any
    source_doc_type: DocumentType
    source_filename: str
    page_number: Optional[int] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.9)
    raw_snippet: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.EXTRACTED


class TimelineEvent(BaseModel):
    """A dated event in the case chronology."""
    event_type: TimelineEventType
    event_date: Optional[date] = None
    description: str
    source_doc_type: DocumentType
    source_filename: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.9)


class ConflictAlert(BaseModel):
    """Raised when different documents disagree on the same fact."""
    field: str
    values: List[Dict[str, Any]]
    alert: str


class CaseExtractionOutput(BaseModel):
    """Schema for Grok structured extraction from a single document."""
    product_name: Optional[str] = None
    product_category: Optional[str] = None
    brand: Optional[str] = None
    model_number: Optional[str] = None
    seller_name: Optional[str] = None
    platform: Optional[str] = Field(None, description="E.g. Amazon, Flipkart, Offline store")
    order_id: Optional[str] = None
    purchase_date: Optional[str] = Field(None, description="ISO YYYY-MM-DD if identifiable")
    delivery_date: Optional[str] = Field(None, description="ISO YYYY-MM-DD if identifiable")
    customer_name: Optional[str] = Field(None, description="Full name of consumer/buyer")
    customer_address: Optional[str] = Field(None, description="Billing or shipping address of consumer")
    customer_phone: Optional[str] = Field(None, description="Contact phone number of consumer")
    customer_email: Optional[str] = Field(None, description="Email address of consumer")
    seller_address: Optional[str] = Field(None, description="Address of seller or store")
    inspection_date: Optional[str] = Field(None, description="Date of technician inspection if identifiable")
    inspection_findings: Optional[str] = Field(None, description="Technician diagnostic finding")
    amount_paid: Optional[float] = Field(None, description="Original purchase price on invoice")
    repair_amount_demanded: Optional[float] = Field(None, description="Quotation or repair amount demanded by service center")
    service_center: Optional[str] = Field(None, description="Name of third-party repair / service center")
    currency: Optional[str] = Field(default="INR")
    warranty_period_months: Optional[int] = None
    warranty_type: Optional[str] = Field(None, description="E.g. manufacturer, seller, extended")
    warranty_exclusions: Optional[str] = None
    defect_date: Optional[str] = Field(None, description="ISO YYYY-MM-DD if identifiable")
    defect_description: Optional[str] = None
    complaint_date: Optional[str] = Field(None, description="ISO YYYY-MM-DD if identifiable")
    seller_response: Optional[str] = None
    seller_response_date: Optional[str] = Field(None, description="ISO YYYY-MM-DD if identifiable")
    resolution_offered: Optional[str] = None
    raw_evidence_quotes: List[str] = Field(
        default_factory=list,
        description="Exact quotes from the document supporting extracted values"
    )


class VisionClassification(BaseModel):
    is_consumer_electronic: bool = Field(
        description="True ONLY if the image clearly shows a consumer electronic device like a phone, laptop, TV, or earbud. False if it is a random object (umbrella, mousetrap, food, etc.)."
    )
    detected_object_name: str = Field(
        description="The primary object in the photo."
    )
    defect_description: Optional[str] = Field(
        default=None,
        description="Only extract if is_consumer_electronic is True. Otherwise, leave null."
    )


class VisionExtractionSchema(BaseModel):
    is_relevant_to_case: bool = Field(
        description="True ONLY IF the image depicts a relevant consumer document or an electronic product/appliance. False if it is a random object (e.g., umbrella, nature, selfie)."
    )
    detected_primary_object: str = Field(
        description="What is the main object in this photo? (e.g., 'Umbrella', 'Laptop Screen', 'Paper Invoice')"
    )
    defect_description: Optional[str] = Field(
        default=None,
        description="Only extract if is_relevant_to_case is True. Otherwise, leave null."
    )
    is_consumer_electronic: Optional[bool] = None
    is_product_match: Optional[bool] = None
    product_match_confidence: Optional[float] = None


class VisionExtractionOutput(BaseModel):
    """Schema for Grok Vision extraction from product/defect photos."""
    is_relevant_to_case: bool = True
    detected_primary_object: Optional[str] = None
    visible_damage: Optional[str] = None
    damage_severity: Optional[str] = Field(None, description="minor, moderate, severe")
    product_identifiable: bool = False
    brand_visible: Optional[str] = None
    model_visible: Optional[str] = None
    serial_number_visible: Optional[str] = None
    additional_observations: Optional[str] = None


class EvidenceChecklistItem(BaseModel):
    """One item in the evidence completeness checklist."""
    item_name: str
    required: bool = True
    status: str = "missing"
    source_filename: Optional[str] = None
    notes: Optional[str] = None


class ScoreDimension(BaseModel):
    """One dimension of the evidence completeness score."""
    dimension: str
    max_score: int
    actual_score: int
    details: str


class RuleCheckResult(BaseModel):
    """Result from the deterministic rules engine."""
    rule_name: str
    rule_status: str
    result: Optional[bool] = None
    summary: str
    details: Dict[str, Any] = Field(default_factory=dict)


class CaseReadinessReport(BaseModel):
    """The final output dossier."""
    case_id: str
    generated_at: datetime
    dispute_type: Optional[DisputeType] = None

    resolved_facts: Dict[str, Any] = Field(default_factory=dict)
    conflicts: List[ConflictAlert] = Field(default_factory=list)

    timeline: List[TimelineEvent] = Field(default_factory=list)

    evidence_checklist: List[EvidenceChecklistItem] = Field(default_factory=list)

    rule_results: List[RuleCheckResult] = Field(default_factory=list)

    relevant_policies: List[Dict[str, Any]] = Field(default_factory=list)

    total_score: int = 0
    max_score: int = 100
    score_breakdown: List[ScoreDimension] = Field(default_factory=list)

    missing_evidence: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    draft_complaint: Optional[str] = None
