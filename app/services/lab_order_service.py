from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.lab_order import (
    AbnormalityFlag,
    LabOrder,
    LabOrderItem,
    LabReport,
    LabResult,
    LabSample,
    OrderItemStatus,
    OrderPriority,
    OrderStatus,
    ReportStatus,
    ResultStatus,
    SampleStatus,
)
from app.models.parameter_reference_range import ParameterReferenceRange
from app.models.patient import Patient
from app.models.test_case import TestCase
from app.models.test_parameter import TestParameter
from app.schemas.lab_order import (
    LabDashboardStats,
    LabOrderCreate,
    LabOrderUpdate,
    LabResultBatchCreate,
    LabSampleCreate,
)


def _get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Number Generators
# ---------------------------------------------------------------------------
def generate_order_number(db: Session) -> str:
    today_str = datetime.now().strftime("%Y%m")
    prefix = f"ORD-{today_str}-"
    last_order = db.scalar(
        select(LabOrder.order_number)
        .where(LabOrder.order_number.like(f"{prefix}%"))
        .order_by(LabOrder.id.desc())
        .limit(1)
    )
    if last_order:
        last_seq = int(last_order.split("-")[-1])
        new_seq = last_seq + 1
    else:
        new_seq = 1
    return f"{prefix}{new_seq:05d}"


def generate_sample_number(db: Session) -> tuple[str, str]:
    today_str = datetime.now().strftime("%Y%m")
    prefix = f"SMP-{today_str}-"
    last_sample = db.scalar(
        select(LabSample.sample_number)
        .where(LabSample.sample_number.like(f"{prefix}%"))
        .order_by(LabSample.id.desc())
        .limit(1)
    )
    if last_sample:
        last_seq = int(last_sample.split("-")[-1])
        new_seq = last_seq + 1
    else:
        new_seq = 1

    sample_num = f"{prefix}{new_seq:05d}"
    barcode = f"BAR-{today_str}-{new_seq:05d}"
    return sample_num, barcode


def generate_report_number(db: Session) -> str:
    today_str = datetime.now().strftime("%Y%m")
    prefix = f"REP-{today_str}-"
    last_report = db.scalar(
        select(LabReport.report_number)
        .where(LabReport.report_number.like(f"{prefix}%"))
        .order_by(LabReport.id.desc())
        .limit(1)
    )
    if last_report:
        last_seq = int(last_report.split("-")[-1])
        new_seq = last_seq + 1
    else:
        new_seq = 1
    return f"{prefix}{new_seq:05d}"


# ---------------------------------------------------------------------------
# Order Lifecycle Management
# ---------------------------------------------------------------------------
def create_lab_order(db: Session, payload: LabOrderCreate, user_id: int) -> LabOrder:
    patient = db.get(Patient, payload.patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    if patient.is_cancelled or not patient.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot place order for an inactive or cancelled patient",
        )

    # Validate test cases
    test_cases = db.scalars(
        select(TestCase).where(TestCase.id.in_(payload.test_case_ids), TestCase.is_active == True)
    ).all()
    found_ids = {tc.id for tc in test_cases}
    missing_ids = set(payload.test_case_ids) - found_ids
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Test cases with IDs {list(missing_ids)} are inactive or not found",
        )

    order_num = generate_order_number(db)
    total_amount = sum((tc.price for tc in test_cases), Decimal("0.00"))

    order = LabOrder(
        order_number=order_num,
        patient_id=payload.patient_id,
        doctor_id=payload.doctor_id,
        collection_center_id=payload.collection_center_id,
        priority=payload.priority,
        status=OrderStatus.PENDING,
        clinical_notes=payload.clinical_notes,
        total_amount=total_amount,
        created_by_id=user_id,
    )
    db.add(order)
    db.flush()

    # Create Order Items and Auto-group Samples by sample_type
    sample_types_needed: set[str] = set()
    for tc in test_cases:
        item = LabOrderItem(
            order_id=order.id,
            test_case_id=tc.id,
            price=tc.price,
            status=OrderItemStatus.ORDERED,
        )
        db.add(item)
        if tc.sample_type:
            sample_types_needed.add(tc.sample_type.strip())
        else:
            sample_types_needed.add("Whole Blood")

    # Automatically initialize primary sample collection records
    for stype in sample_types_needed:
        smp_num, barcode = generate_sample_number(db)
        sample = LabSample(
            sample_number=smp_num,
            barcode=barcode,
            order_id=order.id,
            sample_type=stype,
            container_type=None,
            status=SampleStatus.PENDING_COLLECTION,
        )
        db.add(sample)

    db.commit()
    db.refresh(order)
    return order


def get_lab_order(db: Session, order_id: int) -> LabOrder:
    order = db.scalar(
        select(LabOrder)
        .options(
            joinedload(LabOrder.patient),
            joinedload(LabOrder.doctor),
            selectinload(LabOrder.items).joinedload(LabOrderItem.test_case),
            selectinload(LabOrder.samples),
            selectinload(LabOrder.results).joinedload(LabResult.parameter),
        )
        .where(LabOrder.id == order_id)
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab Order not found")
    return order


def list_lab_orders(
    db: Session,
    patient_id: int | None = None,
    order_number: str | None = None,
    status_filter: OrderStatus | None = None,
    priority_filter: OrderPriority | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[int, list[LabOrder]]:
    query = select(LabOrder).options(
        joinedload(LabOrder.patient),
        joinedload(LabOrder.doctor),
        selectinload(LabOrder.items).joinedload(LabOrderItem.test_case),
        selectinload(LabOrder.samples),
    )

    if patient_id is not None:
        query = query.where(LabOrder.patient_id == patient_id)
    if order_number:
        query = query.where(LabOrder.order_number.ilike(f"%{order_number.strip()}%"))
    if status_filter:
        query = query.where(LabOrder.status == status_filter)
    if priority_filter:
        query = query.where(LabOrder.priority == priority_filter)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    orders = db.scalars(query.order_by(LabOrder.id.desc()).offset(skip).limit(limit)).unique().all()
    return total, list(orders)


def update_lab_order(db: Session, order_id: int, payload: LabOrderUpdate) -> LabOrder:
    order = db.get(LabOrder, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab Order not found")
    if order.is_cancelled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify a cancelled order")

    if payload.priority is not None:
        order.priority = payload.priority
    if payload.clinical_notes is not None:
        order.clinical_notes = payload.clinical_notes

    db.commit()
    db.refresh(order)
    return order


def cancel_lab_order(db: Session, order_id: int, reason: str, user_id: int) -> LabOrder:
    order = db.get(LabOrder, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab Order not found")
    if order.is_cancelled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order is already cancelled")
    if order.status == OrderStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel a completed lab order")

    order.is_cancelled = True
    order.status = OrderStatus.CANCELLED
    order.cancellation_reason = reason
    order.cancelled_at = _get_utc_now()
    order.cancelled_by_id = user_id

    # Cascade cancel order items
    for item in order.items:
        if item.status != OrderItemStatus.VERIFIED:
            item.status = OrderItemStatus.CANCELLED
            item.cancellation_reason = reason

    db.commit()
    db.refresh(order)
    return order


# ---------------------------------------------------------------------------
# Sample Management Workflow
# ---------------------------------------------------------------------------
def collect_sample(db: Session, order_id: int, payload: LabSampleCreate, user_id: int) -> LabSample:
    order = db.get(LabOrder, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab Order not found")
    if order.is_cancelled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order is cancelled")

    smp_num, barcode = generate_sample_number(db)
    sample = LabSample(
        sample_number=smp_num,
        barcode=barcode,
        order_id=order.id,
        sample_type=payload.sample_type,
        container_type=payload.container_type,
        status=SampleStatus.COLLECTED,
        collected_at=_get_utc_now(),
        collected_by_id=user_id,
    )
    db.add(sample)

    if order.status == OrderStatus.PENDING:
        order.status = OrderStatus.SAMPLE_COLLECTED

    db.commit()
    db.refresh(sample)
    return sample


def mark_sample_collected(db: Session, sample_id: int, user_id: int) -> LabSample:
    sample = db.get(LabSample, sample_id)
    if not sample:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")

    sample.status = SampleStatus.COLLECTED
    sample.collected_at = _get_utc_now()
    sample.collected_by_id = user_id

    if sample.order.status == OrderStatus.PENDING:
        sample.order.status = OrderStatus.SAMPLE_COLLECTED

    db.commit()
    db.refresh(sample)
    return sample


def receive_sample_in_lab(db: Session, sample_id: int, user_id: int) -> LabSample:
    sample = db.get(LabSample, sample_id)
    if not sample:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")

    sample.status = SampleStatus.RECEIVED
    sample.received_at = _get_utc_now()
    sample.received_by_id = user_id

    sample.order.status = OrderStatus.PROCESSING
    for item in sample.order.items:
        if item.status in (OrderItemStatus.ORDERED, OrderItemStatus.SAMPLE_COLLECTED):
            item.status = OrderItemStatus.PROCESSING

    db.commit()
    db.refresh(sample)
    return sample


def reject_sample(db: Session, sample_id: int, reason: str, user_id: int) -> LabSample:
    sample = db.get(LabSample, sample_id)
    if not sample:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")

    sample.status = SampleStatus.REJECTED
    sample.rejection_reason = reason
    sample.rejected_at = _get_utc_now()
    sample.rejected_by_id = user_id

    db.commit()
    db.refresh(sample)
    return sample


# ---------------------------------------------------------------------------
# Result Entry & Abnormality Flagging Engine
# ---------------------------------------------------------------------------
def _compute_abnormality(
    db: Session, parameter: TestParameter, numeric_val: Decimal | None, patient: Patient
) -> tuple[AbnormalityFlag, str | None]:
    if numeric_val is None:
        return AbnormalityFlag.NORMAL, parameter.normal_range

    # 1. Critical boundaries check (Panic values)
    if parameter.critical_low:
        try:
            if numeric_val <= Decimal(parameter.critical_low):
                return AbnormalityFlag.CRITICAL, parameter.normal_range
        except Exception:
            pass
    if parameter.critical_high:
        try:
            if numeric_val >= Decimal(parameter.critical_high):
                return AbnormalityFlag.CRITICAL, parameter.normal_range
        except Exception:
            pass

    # 2. Check segmented age/gender reference ranges
    patient_age_days = (patient.age_years * 365) + (patient.age_months * 30) + patient.age_days
    patient_gender = patient.gender.value.lower()

    ref_range = db.scalar(
        select(ParameterReferenceRange)
        .where(
            ParameterReferenceRange.parameter_id == parameter.id,
            ParameterReferenceRange.is_active == True,
            ParameterReferenceRange.min_age_days <= patient_age_days,
            ParameterReferenceRange.max_age_days >= patient_age_days,
            or_(
                ParameterReferenceRange.gender == "all",
                ParameterReferenceRange.gender == patient_gender,
            ),
        )
        .limit(1)
    )

    if ref_range and (ref_range.min_value is not None or ref_range.max_value is not None):
        range_str = ref_range.normal_range_text or f"{ref_range.min_value} - {ref_range.max_value}"
        if ref_range.min_value is not None and numeric_val < ref_range.min_value:
            return AbnormalityFlag.LOW, range_str
        if ref_range.max_value is not None and numeric_val > ref_range.max_value:
            return AbnormalityFlag.HIGH, range_str
        return AbnormalityFlag.NORMAL, range_str

    # 3. Fallback to parameter text normal range
    return AbnormalityFlag.NORMAL, parameter.normal_range


def enter_lab_results(db: Session, order_id: int, payload: LabResultBatchCreate, user_id: int) -> list[LabResult]:
    order = db.get(LabOrder, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab Order not found")
    if order.is_cancelled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot enter results for a cancelled order")

    saved_results: list[LabResult] = []

    for item_data in payload.results:
        order_item = db.get(LabOrderItem, item_data.order_item_id)
        if not order_item or order_item.order_id != order.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid order_item_id {item_data.order_item_id} for this order",
            )

        parameter = db.get(TestParameter, item_data.parameter_id)
        if not parameter or parameter.test_case_id != order_item.test_case_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Parameter {item_data.parameter_id} does not belong to test {order_item.test_case_id}",
            )

        # Parse numeric value if applicable
        numeric_val: Decimal | None = None
        try:
            numeric_val = Decimal(item_data.result_value.strip())
        except Exception:
            numeric_val = None

        flag, ref_range_str = _compute_abnormality(db, parameter, numeric_val, order.patient)

        # Check existing result (update or create)
        existing_result = db.scalar(
            select(LabResult).where(
                LabResult.order_item_id == order_item.id,
                LabResult.parameter_id == parameter.id,
            )
        )

        if existing_result:
            if existing_result.status == ResultStatus.VERIFIED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Result for {parameter.name} is already verified and cannot be edited directly",
                )
            existing_result.result_value = item_data.result_value
            existing_result.numeric_value = numeric_val
            existing_result.abnormality_flag = flag
            existing_result.reference_range = ref_range_str
            existing_result.unit = parameter.unit
            existing_result.comments = item_data.comments
            existing_result.status = ResultStatus.UNDER_VERIFICATION
            existing_result.entered_by_id = user_id
            existing_result.entered_at = _get_utc_now()
            saved_results.append(existing_result)
        else:
            new_result = LabResult(
                order_id=order.id,
                order_item_id=order_item.id,
                parameter_id=parameter.id,
                result_value=item_data.result_value,
                numeric_value=numeric_val,
                unit=parameter.unit,
                reference_range=ref_range_str,
                abnormality_flag=flag,
                status=ResultStatus.UNDER_VERIFICATION,
                comments=item_data.comments,
                entered_by_id=user_id,
                entered_at=_get_utc_now(),
            )
            db.add(new_result)
            saved_results.append(new_result)

        order_item.status = OrderItemStatus.RESULT_ENTERED

    order.status = OrderStatus.PARTIAL_RESULTS
    db.commit()
    for res in saved_results:
        db.refresh(res)
    return saved_results


# ---------------------------------------------------------------------------
# Result Verification & Approval
# ---------------------------------------------------------------------------
def verify_lab_result(db: Session, result_id: int, user_id: int) -> LabResult:
    result = db.get(LabResult, result_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab Result not found")

    result.status = ResultStatus.VERIFIED
    result.verified_by_id = user_id
    result.verified_at = _get_utc_now()

    # Check if all results for this order item are verified
    item_results = db.scalars(select(LabResult).where(LabResult.order_item_id == result.order_item_id)).all()
    if all(r.status == ResultStatus.VERIFIED for r in item_results):
        result.order_item.status = OrderItemStatus.VERIFIED

    # Check if entire order is completed
    all_order_items = result.order.items
    if all(it.status == OrderItemStatus.VERIFIED for it in all_order_items):
        result.order.status = OrderStatus.COMPLETED

    db.commit()
    db.refresh(result)
    return result


def reject_lab_result(db: Session, result_id: int, reason: str, user_id: int) -> LabResult:
    result = db.get(LabResult, result_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab Result not found")

    result.status = ResultStatus.REJECTED
    result.rejection_reason = reason
    result.verified_by_id = user_id
    result.verified_at = _get_utc_now()

    result.order_item.status = OrderItemStatus.PROCESSING

    db.commit()
    db.refresh(result)
    return result


# ---------------------------------------------------------------------------
# Final Verified Report Generation
# ---------------------------------------------------------------------------
def generate_final_report(db: Session, order_id: int, summary_notes: str | None, user_id: int) -> LabReport:
    order = get_lab_order(db, order_id)
    if order.is_cancelled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot generate report for a cancelled order")

    # Strict Clinical Rule: All results must be VERIFIED
    unverified_results = [r for r in order.results if r.status != ResultStatus.VERIFIED]
    if unverified_results:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{len(unverified_results)} result(s) are still pending pathologist verification. Cannot release report.",
        )

    if not order.results:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No test results recorded for this order")

    # Existing report check
    existing_report = db.scalar(select(LabReport).where(LabReport.order_id == order.id))

    # Compile frozen snapshot
    results_snapshot = []
    for r in order.results:
        results_snapshot.append({
            "test_name": r.order_item.test_case.name,
            "parameter_name": r.parameter.name,
            "parameter_code": r.parameter.code,
            "result_value": r.result_value,
            "unit": r.unit,
            "reference_range": r.reference_range,
            "abnormality_flag": r.abnormality_flag.value,
            "comments": r.comments,
            "verified_at": r.verified_at.isoformat() if r.verified_at else None,
        })

    snapshot: dict[str, Any] = {
        "order_number": order.order_number,
        "order_date": order.order_date.isoformat(),
        "patient": {
            "uhid": order.patient.uhid,
            "name": order.patient.name,
            "gender": order.patient.gender.value,
            "age": f"{order.patient.age_years}Y {order.patient.age_months}M",
            "phone": order.patient.phone,
        },
        "doctor": order.doctor.name if order.doctor else "Self / Direct",
        "results": results_snapshot,
    }

    if existing_report:
        existing_report.summary_notes = summary_notes
        existing_report.report_data_snapshot = snapshot
        existing_report.finalized_at = _get_utc_now()
        existing_report.finalized_by_id = user_id
        existing_report.status = ReportStatus.AMENDED
        db.commit()
        db.refresh(existing_report)
        return existing_report

    report_num = generate_report_number(db)
    report = LabReport(
        report_number=report_num,
        order_id=order.id,
        patient_id=order.patient_id,
        status=ReportStatus.RELEASED,
        finalized_at=_get_utc_now(),
        finalized_by_id=user_id,
        summary_notes=summary_notes,
        report_data_snapshot=snapshot,
    )
    order.status = OrderStatus.COMPLETED
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


# ---------------------------------------------------------------------------
# Dashboard Analytics
# ---------------------------------------------------------------------------
def get_lab_dashboard_stats(db: Session) -> LabDashboardStats:
    total_orders = db.scalar(select(func.count(LabOrder.id))) or 0
    pending_orders = db.scalar(select(func.count(LabOrder.id)).where(LabOrder.status == OrderStatus.PENDING)) or 0
    samples_pending = (
        db.scalar(select(func.count(LabSample.id)).where(LabSample.status == SampleStatus.PENDING_COLLECTION)) or 0
    )
    samples_processing = (
        db.scalar(select(func.count(LabSample.id)).where(LabSample.status == SampleStatus.PROCESSING)) or 0
    )
    results_pending = (
        db.scalar(select(func.count(LabResult.id)).where(LabResult.status == ResultStatus.UNDER_VERIFICATION)) or 0
    )
    completed_orders = db.scalar(select(func.count(LabOrder.id)).where(LabOrder.status == OrderStatus.COMPLETED)) or 0
    cancelled_orders = db.scalar(select(func.count(LabOrder.id)).where(LabOrder.status == OrderStatus.CANCELLED)) or 0

    return LabDashboardStats(
        total_orders=total_orders,
        pending_orders=pending_orders,
        samples_pending_collection=samples_pending,
        samples_processing=samples_processing,
        results_pending_verification=results_pending,
        completed_orders=completed_orders,
        cancelled_orders=cancelled_orders,
    )
