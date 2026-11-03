from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.lab_order import OrderPriority, OrderStatus
from app.models.user import UserRole
from app.schemas.lab_order import (
    LabDashboardStats,
    LabOrderCancelRequest,
    LabOrderCreate,
    LabOrderDetailRead,
    LabOrderRead,
    LabOrderUpdate,
    LabReportCreate,
    LabReportRead,
    LabResultBatchCreate,
    LabResultRead,
    LabResultRejectRequest,
    LabSampleCreate,
    LabSampleRead,
    LabSampleRejectRequest,
)
from app.services import lab_order_service

router = APIRouter(prefix="/lab-orders", tags=["Laboratory Orders & Workflow"])


# ---------------------------------------------------------------------------
# Dashboard Analytics Endpoint
# ---------------------------------------------------------------------------
@router.get(
    "/dashboard/stats",
    response_model=LabDashboardStats,
    summary="Get Laboratory Workflow KPIs & Statistics",
)
def get_lab_dashboard(
    db: DbSession,
    _: CurrentUser,
):
    return lab_order_service.get_lab_dashboard_stats(db)


# ---------------------------------------------------------------------------
# Laboratory Order Management
# ---------------------------------------------------------------------------
@router.post(
    "",
    response_model=LabOrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Laboratory Order with Tests",
)
def create_order(
    payload: LabOrderCreate,
    db: DbSession,
    current_user: Annotated[
        CurrentUser,
        Depends(require_roles(UserRole.ADMIN, UserRole.RECEPTIONIST, UserRole.LAB_MANAGER)),
    ],
):
    return lab_order_service.create_lab_order(db, payload, current_user.id)


@router.get(
    "",
    response_model=list[LabOrderRead],
    summary="List Laboratory Orders with Search, Status and Priority Filters",
)
def list_orders(
    db: DbSession,
    _: CurrentUser,
    patient_id: int | None = Query(None, description="Filter by Patient ID"),
    order_number: str | None = Query(None, description="Search by Order Number"),
    status: OrderStatus | None = Query(None, description="Filter by Order Status"),
    priority: OrderPriority | None = Query(None, description="Filter by Priority"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    _, orders = lab_order_service.list_lab_orders(
        db,
        patient_id=patient_id,
        order_number=order_number,
        status_filter=status,
        priority_filter=priority,
        skip=skip,
        limit=limit,
    )
    return orders


@router.get(
    "/{order_id}",
    response_model=LabOrderDetailRead,
    summary="Get Full Laboratory Order Details (Items, Samples, Results)",
)
def get_order_details(
    order_id: int,
    db: DbSession,
    _: CurrentUser,
):
    return lab_order_service.get_lab_order(db, order_id)


@router.get(
    "/patient/{patient_id}",
    response_model=list[LabOrderRead],
    summary="Retrieve Complete Order History for a Specific Patient",
)
def get_patient_order_history(
    patient_id: int,
    db: DbSession,
    _: CurrentUser,
):
    _, orders = lab_order_service.list_lab_orders(db, patient_id=patient_id)
    return orders


@router.patch(
    "/{order_id}",
    response_model=LabOrderRead,
    summary="Update Laboratory Order (Priority or Clinical Notes)",
)
def update_order(
    order_id: int,
    payload: LabOrderUpdate,
    db: DbSession,
    _: Annotated[
        CurrentUser,
        Depends(require_roles(UserRole.ADMIN, UserRole.RECEPTIONIST, UserRole.LAB_MANAGER)),
    ],
):
    return lab_order_service.update_lab_order(db, order_id, payload)


@router.post(
    "/{order_id}/cancel",
    response_model=LabOrderRead,
    summary="Cancel Laboratory Order with Mandatory Reason",
)
def cancel_order(
    order_id: int,
    payload: LabOrderCancelRequest,
    db: DbSession,
    current_user: Annotated[
        CurrentUser,
        Depends(require_roles(UserRole.ADMIN, UserRole.RECEPTIONIST, UserRole.LAB_MANAGER)),
    ],
):
    return lab_order_service.cancel_lab_order(db, order_id, payload.reason, current_user.id)


# ---------------------------------------------------------------------------
# Sample Collection & Tracking
# ---------------------------------------------------------------------------
@router.post(
    "/{order_id}/samples",
    response_model=LabSampleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Collect/Register Specimen Sample (Auto-generates Barcode)",
)
def collect_order_sample(
    order_id: int,
    payload: LabSampleCreate,
    db: DbSession,
    current_user: Annotated[
        CurrentUser,
        Depends(require_roles(UserRole.ADMIN, UserRole.LAB_TECHNICIAN, UserRole.LAB_MANAGER)),
    ],
):
    return lab_order_service.collect_sample(db, order_id, payload, current_user.id)


@router.get(
    "/{order_id}/samples",
    response_model=list[LabSampleRead],
    summary="List all Specimen Samples for an Order",
)
def list_order_samples(
    order_id: int,
    db: DbSession,
    _: CurrentUser,
):
    order = lab_order_service.get_lab_order(db, order_id)
    return order.samples


@router.patch(
    "/samples/{sample_id}/receive",
    response_model=LabSampleRead,
    summary="Mark Specimen Sample as Received in Laboratory",
)
def receive_sample(
    sample_id: int,
    db: DbSession,
    current_user: Annotated[
        CurrentUser,
        Depends(require_roles(UserRole.ADMIN, UserRole.LAB_TECHNICIAN, UserRole.LAB_MANAGER)),
    ],
):
    return lab_order_service.receive_sample_in_lab(db, sample_id, current_user.id)


@router.post(
    "/samples/{sample_id}/reject",
    response_model=LabSampleRead,
    summary="Reject Specimen Sample with Mandatory Reason (e.g. Hemolysis, Clotted)",
)
def reject_sample(
    sample_id: int,
    payload: LabSampleRejectRequest,
    db: DbSession,
    current_user: Annotated[
        CurrentUser,
        Depends(require_roles(UserRole.ADMIN, UserRole.LAB_TECHNICIAN, UserRole.LAB_MANAGER)),
    ],
):
    return lab_order_service.reject_sample(db, sample_id, payload.rejection_reason, current_user.id)


# ---------------------------------------------------------------------------
# Lab Result Entry & Verification Workflow
# ---------------------------------------------------------------------------
@router.post(
    "/{order_id}/results",
    response_model=list[LabResultRead],
    status_code=status.HTTP_201_CREATED,
    summary="Batch Enter Test Parameter Results (Auto flags Normal/Low/High/Critical)",
)
def enter_results(
    order_id: int,
    payload: LabResultBatchCreate,
    db: DbSession,
    current_user: Annotated[
        CurrentUser,
        Depends(require_roles(UserRole.ADMIN, UserRole.LAB_TECHNICIAN, UserRole.LAB_MANAGER)),
    ],
):
    return lab_order_service.enter_lab_results(db, order_id, payload, current_user.id)


@router.get(
    "/{order_id}/results",
    response_model=list[LabResultRead],
    summary="List all Test Parameter Results for an Order",
)
def list_results(
    order_id: int,
    db: DbSession,
    _: CurrentUser,
):
    order = lab_order_service.get_lab_order(db, order_id)
    return order.results


@router.post(
    "/results/{result_id}/verify",
    response_model=LabResultRead,
    summary="Verify & Authorize Test Result (Pathologist/Medical Director Permission Required)",
)
def verify_result(
    result_id: int,
    db: DbSession,
    current_user: Annotated[
        CurrentUser,
        Depends(require_roles(UserRole.ADMIN, UserRole.LAB_MANAGER)),
    ],
):
    return lab_order_service.verify_lab_result(db, result_id, current_user.id)


@router.post(
    "/results/{result_id}/reject",
    response_model=LabResultRead,
    summary="Reject Test Result with Clinical Explanation (Requires rerun/correction)",
)
def reject_result(
    result_id: int,
    payload: LabResultRejectRequest,
    db: DbSession,
    current_user: Annotated[
        CurrentUser,
        Depends(require_roles(UserRole.ADMIN, UserRole.LAB_MANAGER)),
    ],
):
    return lab_order_service.reject_lab_result(db, result_id, payload.reason, current_user.id)


# ---------------------------------------------------------------------------
# Final Verified Report Management
# ---------------------------------------------------------------------------
@router.post(
    "/{order_id}/reports",
    response_model=LabReportRead,
    status_code=status.HTTP_201_CREATED,
    summary="Release Final Verified Laboratory Report (Blocked if unverified results exist)",
)
def generate_report(
    order_id: int,
    payload: LabReportCreate,
    db: DbSession,
    current_user: Annotated[
        CurrentUser,
        Depends(require_roles(UserRole.ADMIN, UserRole.LAB_MANAGER)),
    ],
):
    return lab_order_service.generate_final_report(db, order_id, payload.summary_notes, current_user.id)


@router.get(
    "/{order_id}/reports",
    response_model=LabReportRead,
    summary="Retrieve Final Released Laboratory Report by Order ID",
)
def get_report_by_order(
    order_id: int,
    db: DbSession,
    _: CurrentUser,
):
    order = lab_order_service.get_lab_order(db, order_id)
    if not order.report:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No final report released yet for this order")
    return order.report
