import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from arxi.database import Base


class RxStatus(str, enum.Enum):
    RECEIVED = "received"
    PARSED = "parsed"
    VALIDATED = "validated"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CORRECTED = "corrected"


class RejectionReason(str, enum.Enum):
    CLINICAL_CONCERN = "clinical_concern"
    INCOMPLETE_RX = "incomplete_rx"
    DUR_ISSUE = "dur_issue"
    PRESCRIBER_CONTACT = "prescriber_contact"
    INSURANCE_ISSUE = "insurance_issue"
    PATIENT_SAFETY = "patient_safety"
    OTHER = "other"


class FollowupAction(str, enum.Enum):
    CONTACT_PRESCRIBER = "contact_prescriber"
    CONTACT_PATIENT = "contact_patient"
    REQUEST_PRIOR_AUTH = "request_prior_auth"
    RETURN_TO_PRESCRIBER = "return_to_prescriber"
    NO_ACTION = "no_action"


class ClinicalCheck(str, enum.Enum):
    DUR_REVIEW = "dur_review"
    DRUG_INTERACTIONS = "drug_interactions"
    ALLERGY_SCREENING = "allergy_screening"
    DOSE_RANGE = "dose_range"
    PATIENT_PROFILE = "patient_profile"
    PRESCRIBER_CREDENTIALS = "prescriber_credentials"


class Prescription(Base):
    __tablename__ = "prescriptions"
    __table_args__ = {"schema": "arxi"}

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    status: Mapped[RxStatus] = mapped_column(
        SAEnum(RxStatus, values_callable=lambda e: [m.value for m in e]),
        default=RxStatus.RECEIVED, index=True
    )
    source: Mapped[str] = mapped_column(String(50))  # e-prescribe, fax, phone, manual
    message_id: Mapped[str] = mapped_column(String(100), default="")
    raw_xml: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Patient info (denormalized for quick display)
    patient_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("arxi.patients.id"), nullable=True
    )
    patient_first_name: Mapped[str] = mapped_column(String(100), default="")
    patient_last_name: Mapped[str] = mapped_column(String(100), default="", index=True)
    patient_dob: Mapped[str] = mapped_column(String(10), default="")

    patient: Mapped["Patient | None"] = relationship(
        "Patient", back_populates="prescriptions", lazy="selectin"
    )

    # Prescriber
    prescriber_npi: Mapped[str] = mapped_column(String(10), default="")
    prescriber_dea: Mapped[str] = mapped_column(String(20), default="")
    prescriber_name: Mapped[str] = mapped_column(String(200), default="")

    # Medication
    drug_description: Mapped[str] = mapped_column(String(500), default="")
    ndc: Mapped[str] = mapped_column(String(20), default="", index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    days_supply: Mapped[int] = mapped_column(Integer, default=0)
    refills: Mapped[int] = mapped_column(Integer, default=0)
    sig_text: Mapped[str] = mapped_column(Text, default="")
    written_date: Mapped[str] = mapped_column(String(10), default="")
    substitutions: Mapped[int] = mapped_column(Integer, default=0)

    # Review
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    followup_action: Mapped[str | None] = mapped_column(String(50), nullable=True)
    clinical_checks: Mapped[list | None] = mapped_column(JSON, nullable=True)
    reviewer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # AI Clinical Decision Support
    clinical_findings: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
