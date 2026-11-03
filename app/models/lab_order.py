import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.collection_center import CollectionCenter
    from app.models.doctor import Doctor
    from app.models.patient import Patient
    from app.models.test_case import TestCase
    from app.models.test_parameter import TestParameter
    from app.models.user import User


class OrderPriority(str, enum.Enum):
    ROUTINE = "ROUTINE"
    URGENT = "URGENT"
    STAT = "STAT"  # Emergency / immediate turnaround


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    SAMPLE_COLLECTED = "SAMPLE_COLLECTED"
    PROCESSING = "PROCESSING"
    PARTIAL_RESULTS = "PARTIAL_RESULTS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class OrderItemStatus(str, enum.Enum):
    ORDERED = "ORDERED"
    SAMPLE_PENDING = "SAMPLE_PENDING"
    SAMPLE_COLLECTED = "SAMPLE_COLLECTED"
    PROCESSING = "PROCESSING"
    RESULT_ENTERED = "RESULT_ENTERED"
    UNDER_VERIFICATION = "UNDER_VERIFICATION"
    VERIFIED = "VERIFIED"
    CANCELLED = "CANCELLED"


class SampleStatus(str, enum.Enum):
    PENDING_COLLECTION = "PENDING_COLLECTION"
    COLLECTED = "COLLECTED"
    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    REJECTED = "REJECTED"
    RECOLLECTION_REQUIRED = "RECOLLECTION_REQUIRED"
    COMPLETED = "COMPLETED"


class AbnormalityFlag(str, enum.Enum):
    NORMAL = "NORMAL"
    LOW = "LOW"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ResultStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    UNDER_VERIFICATION = "UNDER_VERIFICATION"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class ReportStatus(str, enum.Enum):
    GENERATED = "GENERATED"
    RELEASED = "RELEASED"
    AMENDED = "AMENDED"


class LabOrder(Base):
    __tablename__ = "lab_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    doctor_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("doctors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    collection_center_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("collection_centers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    priority: Mapped[OrderPriority] = mapped_column(
        Enum(OrderPriority, name="order_priority", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=OrderPriority.ROUTINE,
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=OrderStatus.PENDING,
    )

    order_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    clinical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Financial snapshots
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    # Cancellation audit
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # General audit
    created_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient")
    doctor: Mapped["Doctor | None"] = relationship("Doctor")
    collection_center: Mapped["CollectionCenter | None"] = relationship("CollectionCenter")
    created_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_id])
    cancelled_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[cancelled_by_id])

    items: Mapped[list["LabOrderItem"]] = relationship(
        "LabOrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    samples: Mapped[list["LabSample"]] = relationship(
        "LabSample",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    results: Mapped[list["LabResult"]] = relationship(
        "LabResult",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    report: Mapped["LabReport | None"] = relationship(
        "LabReport",
        back_populates="order",
        uselist=False,
        cascade="all, delete-orphan",
    )


class LabOrderItem(Base):
    __tablename__ = "lab_order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lab_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_case_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("test_cases.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    status: Mapped[OrderItemStatus] = mapped_column(
        Enum(OrderItemStatus, name="order_item_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=OrderItemStatus.ORDERED,
    )
    cancellation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    order: Mapped["LabOrder"] = relationship("LabOrder", back_populates="items")
    test_case: Mapped["TestCase"] = relationship("TestCase")
    results: Mapped[list["LabResult"]] = relationship("LabResult", back_populates="order_item")


class LabSample(Base):
    __tablename__ = "lab_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sample_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    barcode: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lab_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sample_type: Mapped[str] = mapped_column(String(100), nullable=False)  # EDTA, Serum, Urine, etc.
    container_type: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Purple Top, Yellow Top, etc.

    status: Mapped[SampleStatus] = mapped_column(
        Enum(SampleStatus, name="sample_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=SampleStatus.PENDING_COLLECTION,
    )

    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    collected_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    order: Mapped["LabOrder"] = relationship("LabOrder", back_populates="samples")
    collected_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[collected_by_id])
    received_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[received_by_id])


class LabResult(Base):
    __tablename__ = "lab_results"

    __table_args__ = (
        UniqueConstraint(
            "order_item_id",
            "parameter_id",
            name="uq_lab_results_item_parameter",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lab_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lab_order_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parameter_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("test_parameters.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    result_value: Mapped[str] = mapped_column(String(255), nullable=False)
    numeric_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reference_range: Mapped[str | None] = mapped_column(String(255), nullable=True)

    abnormality_flag: Mapped[AbnormalityFlag] = mapped_column(
        Enum(AbnormalityFlag, name="abnormality_flag", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=AbnormalityFlag.NORMAL,
    )

    status: Mapped[ResultStatus] = mapped_column(
        Enum(ResultStatus, name="result_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ResultStatus.DRAFT,
    )

    comments: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Result Entry Audit
    entered_by_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    entered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Verification / Approval Audit
    verified_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    order: Mapped["LabOrder"] = relationship("LabOrder", back_populates="results")
    order_item: Mapped["LabOrderItem"] = relationship("LabOrderItem", back_populates="results")
    parameter: Mapped["TestParameter"] = relationship("TestParameter")
    entered_by_user: Mapped["User"] = relationship("User", foreign_keys=[entered_by_id])
    verified_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[verified_by_id])


class LabReport(Base):
    __tablename__ = "lab_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lab_orders.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ReportStatus.GENERATED,
    )

    finalized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    finalized_by_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    summary_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_data_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    order: Mapped["LabOrder"] = relationship("LabOrder", back_populates="report")
    patient: Mapped["Patient"] = relationship("Patient")
    finalized_by_user: Mapped["User"] = relationship("User", foreign_keys=[finalized_by_id])
