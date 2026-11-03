from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.lab_order import (
    AbnormalityFlag,
    OrderItemStatus,
    OrderPriority,
    OrderStatus,
    ReportStatus,
    ResultStatus,
    SampleStatus,
)


# -------------------------------------------------------------
# Base Schemas
# -------------------------------------------------------------
class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Test Catalog & Parameter Mini Schemas
# -------------------------------------------------------------
class TestParameterSummary(OrmModel):
    id: int
    name: str
    code: str
    unit: str | None = None
    normal_range: str | None = None
    data_type: str
    options: str | None = None
    critical_low: str | None = None
    critical_high: str | None = None
    is_required: bool
    display_order: int


class TestCaseSummary(OrmModel):
    id: int
    name: str
    code: str
    sample_type: str | None = None
    price: Decimal
    tat: str | None = None
    department_id: int | None = None


# -------------------------------------------------------------
# Lab Order Item Schemas
# -------------------------------------------------------------
class LabOrderItemCreate(BaseModel):
    test_case_id: int


class LabOrderItemRead(OrmModel):
    id: int
    order_id: int
    test_case_id: int
    price: Decimal
    status: OrderItemStatus
    cancellation_reason: str | None = None
    created_at: datetime
    test_case: TestCaseSummary | None = None


# -------------------------------------------------------------
# Lab Sample Schemas
# -------------------------------------------------------------
class LabSampleCreate(BaseModel):
    sample_type: str = Field(..., example="EDTA Whole Blood")
    container_type: str | None = Field(None, example="Purple Top / EDTA Tube")


class LabSampleRead(OrmModel):
    id: int
    sample_number: str
    barcode: str
    order_id: int
    sample_type: str
    container_type: str | None = None
    status: SampleStatus
    collected_at: datetime | None = None
    collected_by_id: int | None = None
    received_at: datetime | None = None
    received_by_id: int | None = None
    rejection_reason: str | None = None
    rejected_at: datetime | None = None
    created_at: datetime


class LabSampleRejectRequest(BaseModel):
    rejection_reason: str = Field(..., min_length=3, max_length=500, example="Hemolyzed sample, recollection required")


# -------------------------------------------------------------
# Lab Result Schemas
# -------------------------------------------------------------
class LabResultEntryItem(BaseModel):
    order_item_id: int
    parameter_id: int
    result_value: str = Field(..., example="14.2")
    comments: str | None = None


class LabResultBatchCreate(BaseModel):
    results: list[LabResultEntryItem]


class LabResultRead(OrmModel):
    id: int
    order_id: int
    order_item_id: int
    parameter_id: int
    result_value: str
    numeric_value: Decimal | None = None
    unit: str | None = None
    reference_range: str | None = None
    abnormality_flag: AbnormalityFlag
    status: ResultStatus
    comments: str | None = None
    entered_by_id: int
    entered_at: datetime
    verified_by_id: int | None = None
    verified_at: datetime | None = None
    rejection_reason: str | None = None
    created_at: datetime
    parameter: TestParameterSummary | None = None


class LabResultRejectRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500, example="Result inconsistent with previous baseline, please rerun")


# -------------------------------------------------------------
# Lab Order Schemas
# -------------------------------------------------------------
class LabOrderCreate(BaseModel):
    patient_id: int
    doctor_id: int | None = None
    collection_center_id: int | None = None
    priority: OrderPriority = OrderPriority.ROUTINE
    clinical_notes: str | None = None
    test_case_ids: list[int] = Field(..., min_length=1, description="List of test case IDs to order")


class LabOrderUpdate(BaseModel):
    priority: OrderPriority | None = None
    clinical_notes: str | None = None


class LabOrderCancelRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500, example="Patient cancelled OPD registration")


class PatientSummary(OrmModel):
    id: int
    uhid: str
    name: str
    gender: str
    age_years: int
    age_months: int
    age_days: int
    phone: str | None = None
    email: str | None = None


class DoctorSummary(OrmModel):
    id: int
    name: str
    specialization: str | None = None
    phone: str | None = None


class LabOrderRead(OrmModel):
    id: int
    order_number: str
    patient_id: int
    doctor_id: int | None = None
    collection_center_id: int | None = None
    priority: OrderPriority
    status: OrderStatus
    order_date: datetime
    clinical_notes: str | None = None
    total_amount: Decimal
    is_cancelled: bool
    cancellation_reason: str | None = None
    cancelled_at: datetime | None = None
    created_by_id: int | None = None
    created_at: datetime
    updated_at: datetime

    patient: PatientSummary | None = None
    doctor: DoctorSummary | None = None
    items: list[LabOrderItemRead] = []
    samples: list[LabSampleRead] = []


class LabOrderDetailRead(LabOrderRead):
    results: list[LabResultRead] = []


# -------------------------------------------------------------
# Lab Report Schemas
# -------------------------------------------------------------
class LabReportCreate(BaseModel):
    summary_notes: str | None = None


class LabReportRead(OrmModel):
    id: int
    report_number: str
    order_id: int
    patient_id: int
    status: ReportStatus
    finalized_at: datetime
    finalized_by_id: int
    summary_notes: str | None = None
    report_data_snapshot: dict[str, Any] | None = None
    created_at: datetime


# -------------------------------------------------------------
# Laboratory Dashboard KPIs Schema
# -------------------------------------------------------------
class LabDashboardStats(BaseModel):
    total_orders: int
    pending_orders: int
    samples_pending_collection: int
    samples_processing: int
    results_pending_verification: int
    completed_orders: int
    cancelled_orders: int
