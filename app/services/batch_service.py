from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.batch_processor import SagaBatchProcessor
from app.models.accommodation import Accommodation, AccommodationStatus
from app.models.booking import Booking, BookingStatus, PaymentStatus
from app.schemas.batch import (
    AccommodationStatusUpdateOperation,
    BatchJobResult,
    BatchOperationItem,
    BatchOperationType,
    BatchRequest,
    BookingCancelOperation,
    BookingSetDatesOperation,
    BookingStatusUpdateOperation,
    BulkBookingConfirmation,
    BulkDateAssignment,
)


class BatchOperationService:
    """Service for handling batch operations with Saga pattern transaction safety."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.processor = SagaBatchProcessor(db)

    async def bulk_update_booking_status(
        self,
        operation: BookingStatusUpdateOperation,
        user_id: Optional[int] = None,
        dry_run: bool = False,
    ) -> BatchJobResult:
        """Bulk update booking statuses with validation and rollback capability."""

        # Validate all bookings exist and can be updated
        validation_errors = await self._validate_bookings_for_status_update(
            operation.booking_ids, operation.new_status
        )

        if validation_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation errors: {validation_errors}",
            )

        # Create batch operations
        batch_operations = []
        for booking_id in operation.booking_ids:
            batch_op = BatchOperationItem(
                target_id=booking_id,
                operation_type=BatchOperationType.BOOKING_STATUS_UPDATE,
                parameters={
                    "new_status": operation.new_status.value,
                    "reason": operation.reason,
                    "notify_clients": operation.notify_clients,
                },
            )
            batch_operations.append(batch_op)

        # Create batch request
        batch_request = BatchRequest(
            job_name=f"Bulk Status Update: {len(operation.booking_ids)} bookings to {operation.new_status.value}",
            description=f"Update booking status to {operation.new_status.value}. Reason: {operation.reason}",
            operations=batch_operations,
            dry_run=dry_run,
            fail_fast=True,
            enable_compensation=True,
        )

        # Execute batch
        return await self.processor.execute_batch(batch_request, user_id)

    async def bulk_cancel_bookings(
        self,
        operation: BookingCancelOperation,
        user_id: Optional[int] = None,
        dry_run: bool = False,
    ) -> BatchJobResult:
        """Bulk cancel bookings with optional refund processing."""

        # Validate all bookings can be cancelled
        validation_errors = await self._validate_bookings_for_cancellation(
            operation.booking_ids
        )

        if validation_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation errors: {validation_errors}",
            )

        # Create batch operations
        batch_operations = []
        for booking_id in operation.booking_ids:
            batch_op = BatchOperationItem(
                target_id=booking_id,
                operation_type=BatchOperationType.BOOKING_CANCEL,
                parameters={
                    "cancellation_reason": operation.cancellation_reason,
                    "refund_amount": operation.refund_amount,
                    "notify_clients": operation.notify_clients,
                },
            )
            batch_operations.append(batch_op)

        # Create batch request
        batch_request = BatchRequest(
            job_name=f"Bulk Cancellation: {len(operation.booking_ids)} bookings",
            description=f"Cancel bookings. Reason: {operation.cancellation_reason}",
            operations=batch_operations,
            dry_run=dry_run,
            fail_fast=False,  # Continue cancelling even if some fail
            enable_compensation=True,
        )

        # Execute batch
        return await self.processor.execute_batch(batch_request, user_id)

    async def bulk_set_booking_dates(
        self,
        operation: BookingSetDatesOperation,
        user_id: Optional[int] = None,
        dry_run: bool = False,
    ) -> BatchJobResult:
        """Bulk set dates for open-date bookings with availability validation."""

        # Validate date assignments
        validation_errors = await self._validate_date_assignments(
            operation.booking_date_assignments, operation.validate_availability
        )

        if validation_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation errors: {validation_errors}",
            )

        # Create batch operations
        batch_operations = []
        for assignment in operation.booking_date_assignments:
            batch_op = BatchOperationItem(
                target_id=assignment["booking_id"],
                operation_type=BatchOperationType.BOOKING_SET_DATES,
                parameters={
                    "check_in_date": assignment["check_in_date"],
                    "check_out_date": assignment["check_out_date"],
                    "validate_availability": operation.validate_availability,
                },
            )
            batch_operations.append(batch_op)

        # Create batch request
        batch_request = BatchRequest(
            job_name=f"Bulk Date Assignment: {len(operation.booking_date_assignments)} bookings",
            description="Assign dates to open-date bookings",
            operations=batch_operations,
            dry_run=dry_run,
            fail_fast=True,  # Stop if availability conflicts
            enable_compensation=True,
        )

        # Execute batch
        return await self.processor.execute_batch(batch_request, user_id)

    async def bulk_update_accommodation_status(
        self,
        operation: AccommodationStatusUpdateOperation,
        user_id: Optional[int] = None,
        dry_run: bool = False,
    ) -> BatchJobResult:
        """Bulk update accommodation statuses."""

        # Validate accommodations exist
        validation_errors = await self._validate_accommodations_exist(
            operation.accommodation_ids
        )

        if validation_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation errors: {validation_errors}",
            )

        # Create batch operations
        batch_operations = []
        for accommodation_id in operation.accommodation_ids:
            batch_op = BatchOperationItem(
                target_id=accommodation_id,
                operation_type=BatchOperationType.ACCOMMODATION_STATUS_UPDATE,
                parameters={
                    "new_status": operation.new_status.value,
                    "new_condition": operation.new_condition.value
                    if operation.new_condition
                    else None,
                    "reason": operation.reason,
                    "maintenance_notes": operation.maintenance_notes,
                },
            )
            batch_operations.append(batch_op)

        # Create batch request
        batch_request = BatchRequest(
            job_name=f"Bulk Accommodation Status Update: {len(operation.accommodation_ids)} accommodations",
            description=f"Update accommodation status to {operation.new_status.value}. Reason: {operation.reason}",
            operations=batch_operations,
            dry_run=dry_run,
            fail_fast=False,
            enable_compensation=True,
        )

        # Execute batch
        return await self.processor.execute_batch(batch_request, user_id)

    async def bulk_confirm_bookings(
        self,
        operation: BulkBookingConfirmation,
        user_id: Optional[int] = None,
        dry_run: bool = False,
    ) -> BatchJobResult:
        """Bulk confirm bookings with payment validation."""

        # Validate bookings can be confirmed
        validation_errors = []

        for booking_id in operation.booking_ids:
            booking = await self._get_booking_by_id(booking_id)
            if not booking:
                validation_errors.append(f"Booking {booking_id} not found")
                continue

            if booking.status != BookingStatus.PENDING:
                validation_errors.append(
                    f"Booking {booking_id} is not in PENDING status"
                )
                continue

            if (
                operation.require_full_payment
                and booking.payment_status != PaymentStatus.PAID
            ):
                validation_errors.append(
                    f"Booking {booking_id} does not have full payment"
                )

        if validation_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation errors: {validation_errors}",
            )

        # Create status update operation
        status_operation = BookingStatusUpdateOperation(
            booking_ids=operation.booking_ids,
            new_status=BookingStatus.CONFIRMED,
            reason="Bulk confirmation",
            notify_clients=operation.send_confirmation_emails,
        )

        return await self.bulk_update_booking_status(status_operation, user_id, dry_run)

    async def bulk_assign_dates(
        self,
        operation: BulkDateAssignment,
        user_id: Optional[int] = None,
        dry_run: bool = False,
    ) -> BatchJobResult:
        """Bulk assign dates to open-date bookings with smart accommodation assignment."""

        processed_assignments = []

        # Process each assignment and auto-assign accommodations if needed
        for assignment in operation.assignments:
            booking_id = assignment["booking_id"]
            check_in_date = assignment["check_in_date"]
            check_out_date = assignment["check_out_date"]
            accommodation_id = assignment.get("accommodation_id")

            # Auto-assign accommodation if not specified
            if not accommodation_id and operation.auto_assign_accommodations:
                accommodation_id = await self._find_available_accommodation(
                    check_in_date,
                    check_out_date,
                    operation.preferred_accommodation_types,
                )
                if not accommodation_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"No available accommodation found for booking {booking_id} on {check_in_date} to {check_out_date}",
                    )

            processed_assignments.append(
                {
                    "booking_id": booking_id,
                    "check_in_date": check_in_date,
                    "check_out_date": check_out_date,
                    "accommodation_id": accommodation_id,
                }
            )

        # Create date assignment operation
        date_operation = BookingSetDatesOperation(
            booking_date_assignments=processed_assignments,
            validate_availability=operation.validate_accommodation_availability,
        )

        return await self.bulk_set_booking_dates(date_operation, user_id, dry_run)

    # Validation methods
    async def _validate_bookings_for_status_update(
        self, booking_ids: List[int], new_status: BookingStatus
    ) -> List[str]:
        """Validate that bookings can be updated to the new status."""
        errors = []

        # Get all bookings
        stmt = select(Booking).where(Booking.id.in_(booking_ids))
        result = await self.db.execute(stmt)
        bookings = result.scalars().all()

        found_ids = {booking.id for booking in bookings}
        missing_ids = set(booking_ids) - found_ids

        for missing_id in missing_ids:
            errors.append(f"Booking {missing_id} not found")

        # Validate status transitions
        for booking in bookings:
            if not self._is_valid_status_transition(booking.status, new_status):
                errors.append(
                    f"Invalid status transition for booking {booking.id}: {booking.status} -> {new_status}"
                )

        return errors

    async def _validate_bookings_for_cancellation(
        self, booking_ids: List[int]
    ) -> List[str]:
        """Validate that bookings can be cancelled."""
        errors = []

        stmt = select(Booking).where(Booking.id.in_(booking_ids))
        result = await self.db.execute(stmt)
        bookings = result.scalars().all()

        found_ids = {booking.id for booking in bookings}
        missing_ids = set(booking_ids) - found_ids

        for missing_id in missing_ids:
            errors.append(f"Booking {missing_id} not found")

        for booking in bookings:
            if booking.status in [BookingStatus.CANCELLED, BookingStatus.CHECKED_OUT]:
                errors.append(
                    f"Booking {booking.id} cannot be cancelled (status: {booking.status})"
                )

        return errors

    async def _validate_date_assignments(
        self, assignments: List[Dict[str, Any]], validate_availability: bool
    ) -> List[str]:
        """Validate date assignments for bookings."""
        errors = []

        booking_ids = [a["booking_id"] for a in assignments]
        stmt = select(Booking).where(Booking.id.in_(booking_ids))
        result = await self.db.execute(stmt)
        bookings = {booking.id: booking for booking in result.scalars().all()}

        for assignment in assignments:
            booking_id = assignment["booking_id"]
            check_in_date = assignment["check_in_date"]
            check_out_date = assignment["check_out_date"]

            # Check booking exists
            booking = bookings.get(booking_id)
            if not booking:
                errors.append(f"Booking {booking_id} not found")
                continue

            # Check booking is open dates
            if not booking.is_open_dates:
                errors.append(f"Booking {booking_id} is not an open-dates booking")
                continue

            # Validate date range
            if check_in_date >= check_out_date:
                errors.append(
                    f"Invalid date range for booking {booking_id}: check-in must be before check-out"
                )
                continue

            # Check availability if requested
            if validate_availability:
                available = await self._check_accommodation_availability(
                    booking.accommodation_id, check_in_date, check_out_date, booking_id
                )
                if not available:
                    errors.append(
                        f"Accommodation not available for booking {booking_id} on {check_in_date} to {check_out_date}"
                    )

        return errors

    async def _validate_accommodations_exist(
        self, accommodation_ids: List[int]
    ) -> List[str]:
        """Validate that accommodations exist."""
        errors = []

        stmt = select(Accommodation.id).where(Accommodation.id.in_(accommodation_ids))
        result = await self.db.execute(stmt)
        found_ids = {row[0] for row in result.all()}

        missing_ids = set(accommodation_ids) - found_ids
        for missing_id in missing_ids:
            errors.append(f"Accommodation {missing_id} not found")

        return errors

    # Helper methods
    def _is_valid_status_transition(
        self, current_status: BookingStatus, new_status: BookingStatus
    ) -> bool:
        """Check if status transition is valid."""
        valid_transitions = {
            BookingStatus.PENDING: [BookingStatus.CONFIRMED, BookingStatus.CANCELLED],
            BookingStatus.CONFIRMED: [
                BookingStatus.CHECKED_IN,
                BookingStatus.CANCELLED,
            ],
            BookingStatus.CHECKED_IN: [BookingStatus.CHECKED_OUT],
            BookingStatus.CHECKED_OUT: [],
            BookingStatus.CANCELLED: [],
        }

        return new_status in valid_transitions.get(current_status, [])

    async def _get_booking_by_id(self, booking_id: int) -> Optional[Booking]:
        """Get booking by ID."""
        stmt = select(Booking).where(Booking.id == booking_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _check_accommodation_availability(
        self,
        accommodation_id: int,
        check_in_date: date,
        check_out_date: date,
        exclude_booking_id: Optional[int] = None,
    ) -> bool:
        """Check if accommodation is available for given dates."""
        from app.services.booking_service import BookingService

        booking_service = BookingService(self.db)
        return await booking_service.check_availability(
            accommodation_id, check_in_date, check_out_date, exclude_booking_id
        )

    async def _find_available_accommodation(
        self,
        check_in_date: date,
        check_out_date: date,
        preferred_types: Optional[List[int]] = None,
    ) -> Optional[int]:
        """Find an available accommodation for the given dates."""
        # Build accommodation query
        stmt = select(Accommodation).where(
            Accommodation.status == AccommodationStatus.AVAILABLE
        )

        if preferred_types:
            stmt = stmt.where(Accommodation.type_id.in_(preferred_types))

        result = await self.db.execute(stmt)
        accommodations = result.scalars().all()

        # Check availability for each accommodation
        for accommodation in accommodations:
            available = await self._check_accommodation_availability(
                accommodation.id, check_in_date, check_out_date
            )
            if available:
                return accommodation.id

        return None
