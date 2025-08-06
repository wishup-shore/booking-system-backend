from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.core.common_deps import BatchOperationServiceDep, CurrentUserDep, StaffUserDep
from app.schemas.batch import (
    AccommodationStatusUpdateOperation,
    BatchJobResult,
    BatchRequest,
    BookingCancelOperation,
    BookingSetDatesOperation,
    BookingStatusUpdateOperation,
    BulkBookingConfirmation,
    BulkDateAssignment,
)

router = APIRouter()


# Booking batch operations
@router.post("/bookings/status-update", response_model=BatchJobResult)
async def bulk_update_booking_status(
    operation: BookingStatusUpdateOperation,
    service: BatchOperationServiceDep,
    current_user: StaffUserDep,
    dry_run: bool = Query(False, description="Preview changes without executing"),
):
    """Bulk update booking statuses with transaction safety."""
    return await service.bulk_update_booking_status(operation, current_user.id, dry_run)


@router.post("/bookings/cancel", response_model=BatchJobResult)
async def bulk_cancel_bookings(
    operation: BookingCancelOperation,
    service: BatchOperationServiceDep,
    current_user: StaffUserDep,
    dry_run: bool = Query(False, description="Preview changes without executing"),
):
    """Bulk cancel bookings with optional refund processing."""
    return await service.bulk_cancel_bookings(operation, current_user.id, dry_run)


@router.post("/bookings/set-dates", response_model=BatchJobResult)
async def bulk_set_booking_dates(
    operation: BookingSetDatesOperation,
    service: BatchOperationServiceDep,
    current_user: StaffUserDep,
    dry_run: bool = Query(False, description="Preview changes without executing"),
):
    """Bulk assign dates to open-date bookings with availability validation."""
    return await service.bulk_set_booking_dates(operation, current_user.id, dry_run)


@router.post("/bookings/confirm", response_model=BatchJobResult)
async def bulk_confirm_bookings(
    operation: BulkBookingConfirmation,
    service: BatchOperationServiceDep,
    current_user: StaffUserDep,
    dry_run: bool = Query(False, description="Preview changes without executing"),
):
    """Bulk confirm bookings with payment validation."""
    return await service.bulk_confirm_bookings(operation, current_user.id, dry_run)


@router.post("/bookings/assign-dates", response_model=BatchJobResult)
async def bulk_assign_dates_to_bookings(
    operation: BulkDateAssignment,
    service: BatchOperationServiceDep,
    current_user: StaffUserDep,
    dry_run: bool = Query(False, description="Preview changes without executing"),
):
    """Bulk assign dates to open-date bookings with smart accommodation assignment."""
    return await service.bulk_assign_dates(operation, current_user.id, dry_run)


# Accommodation batch operations
@router.post("/accommodations/status-update", response_model=BatchJobResult)
async def bulk_update_accommodation_status(
    operation: AccommodationStatusUpdateOperation,
    service: BatchOperationServiceDep,
    current_user: StaffUserDep,
    dry_run: bool = Query(False, description="Preview changes without executing"),
):
    """Bulk update accommodation statuses."""
    return await service.bulk_update_accommodation_status(
        operation, current_user.id, dry_run
    )


# Generic batch operation endpoint
@router.post("/execute", response_model=BatchJobResult)
async def execute_batch_operation(
    batch_request: BatchRequest,
    background_tasks: BackgroundTasks,
    service: BatchOperationServiceDep,
    current_user: StaffUserDep,
):
    """Execute a custom batch operation with Saga pattern transaction safety."""
    if batch_request.execute_at:
        # Schedule for later execution (would require background job system)
        raise HTTPException(
            status_code=501,
            detail="Scheduled batch operations not yet implemented. Use background job system.",
        )

    # Execute immediately
    return await service.processor.execute_batch(batch_request, current_user.id)


# Batch operation examples and templates
@router.get("/examples/booking-status-update")
async def get_booking_status_update_example():
    """Get example payload for booking status update operation."""
    return {
        "example": {
            "booking_ids": [1, 2, 3],
            "new_status": "CONFIRMED",
            "reason": "Payment received",
            "notify_clients": True,
        },
        "description": "Update multiple bookings to CONFIRMED status",
        "endpoint": "POST /api/v1/batch/bookings/status-update",
    }


@router.get("/examples/booking-cancel")
async def get_booking_cancel_example():
    """Get example payload for booking cancellation operation."""
    return {
        "example": {
            "booking_ids": [1, 2, 3],
            "cancellation_reason": "Client requested cancellation",
            "refund_amount": 100.0,
            "notify_clients": True,
        },
        "description": "Cancel multiple bookings with refund",
        "endpoint": "POST /api/v1/batch/bookings/cancel",
    }


@router.get("/examples/booking-set-dates")
async def get_booking_set_dates_example():
    """Get example payload for setting dates on open-date bookings."""
    return {
        "example": {
            "booking_date_assignments": [
                {
                    "booking_id": 1,
                    "check_in_date": "2025-08-15",
                    "check_out_date": "2025-08-18",
                },
                {
                    "booking_id": 2,
                    "check_in_date": "2025-08-20",
                    "check_out_date": "2025-08-22",
                },
            ],
            "validate_availability": True,
        },
        "description": "Assign specific dates to open-date bookings",
        "endpoint": "POST /api/v1/batch/bookings/set-dates",
    }


@router.get("/examples/accommodation-status-update")
async def get_accommodation_status_update_example():
    """Get example payload for accommodation status update operation."""
    return {
        "example": {
            "accommodation_ids": [1, 2, 3],
            "new_status": "MAINTENANCE",
            "new_condition": "MINOR_ISSUE",
            "reason": "Scheduled maintenance",
            "maintenance_notes": "Plumbing repair required",
        },
        "description": "Update multiple accommodations to maintenance status",
        "endpoint": "POST /api/v1/batch/accommodations/status-update",
    }


@router.get("/examples/bulk-confirmation")
async def get_bulk_confirmation_example():
    """Get example payload for bulk booking confirmation."""
    return {
        "example": {
            "booking_ids": [1, 2, 3],
            "require_full_payment": True,
            "send_confirmation_emails": True,
            "confirmation_message": "Your booking has been confirmed!",
        },
        "description": "Confirm multiple bookings with payment validation",
        "endpoint": "POST /api/v1/batch/bookings/confirm",
    }


@router.get("/examples/bulk-date-assignment")
async def get_bulk_date_assignment_example():
    """Get example payload for bulk date assignment with auto-accommodation."""
    return {
        "example": {
            "assignments": [
                {
                    "booking_id": 1,
                    "check_in_date": "2025-08-15",
                    "check_out_date": "2025-08-18",
                },
                {
                    "booking_id": 2,
                    "check_in_date": "2025-08-20",
                    "check_out_date": "2025-08-22",
                    "accommodation_id": 5,
                },
            ],
            "validate_accommodation_availability": True,
            "auto_assign_accommodations": True,
            "preferred_accommodation_types": [1, 2],
        },
        "description": "Assign dates to bookings with smart accommodation assignment",
        "endpoint": "POST /api/v1/batch/bookings/assign-dates",
    }


# Batch operation utilities
@router.post("/validate")
async def validate_batch_operation(
    batch_request: BatchRequest,
    service: BatchOperationServiceDep,
    current_user: StaffUserDep,
):
    """Validate a batch operation without executing it."""
    # Set dry_run to true for validation
    batch_request.dry_run = True

    try:
        result = await service.processor.execute_batch(batch_request, current_user.id)
        return {
            "valid": True,
            "estimated_execution_time_ms": result.total_execution_time_ms,
            "total_operations": result.total_operations,
            "dry_run_results": [
                {
                    "operation_id": op.operation_id,
                    "target_id": op.target_id,
                    "operation_type": op.operation_type,
                    "success": op.success,
                    "error_message": op.error_message,
                }
                for op in result.operation_results
            ],
        }
    except Exception as e:
        return {"valid": False, "error": str(e), "validation_failed": True}


# Operational endpoints for batch management
@router.get("/status/{job_id}")
async def get_batch_job_status(
    job_id: str,
    current_user: CurrentUserDep,
):
    """Get the status of a batch job (for future background job implementation)."""
    return {
        "message": "Batch job status tracking not yet implemented",
        "job_id": job_id,
        "suggestion": "Use background job system like Celery for long-running batch operations",
    }


@router.post("/cancel/{job_id}")
async def cancel_batch_job(
    job_id: str,
    current_user: StaffUserDep,
):
    """Cancel a running batch job (for future background job implementation)."""
    return {
        "message": "Batch job cancellation not yet implemented",
        "job_id": job_id,
        "suggestion": "Implement with background job system for cancellation support",
    }
