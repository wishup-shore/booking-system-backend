import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.batch import (
    BatchJobResult,
    BatchJobStatus,
    BatchOperationItem,
    BatchOperationResult,
    BatchOperationStatus,
    BatchOperationType,
    BatchRequest,
    BatchValidationError,
    BatchValidationResult,
    CompensationOperation,
    SagaTransaction,
)

logger = logging.getLogger(__name__)


class BatchProcessorError(Exception):
    """Base exception for batch processing errors."""

    pass


class CompensationError(Exception):
    """Exception raised during compensation operations."""

    pass


@dataclass
class OperationContext:
    """Context information for operation execution."""

    db: AsyncSession
    operation: BatchOperationItem
    job_id: str
    user_id: Optional[int] = None
    dry_run: bool = False


class SagaBatchProcessor:
    """
    Saga pattern implementation for batch operations with compensation.
    Provides transaction safety for complex multi-step batch operations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.operation_handlers: Dict[BatchOperationType, Callable] = {}
        self.compensation_handlers: Dict[BatchOperationType, Callable] = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default operation and compensation handlers."""
        # Booking operation handlers
        self.operation_handlers[BatchOperationType.BOOKING_STATUS_UPDATE] = (
            self._handle_booking_status_update
        )
        self.operation_handlers[BatchOperationType.BOOKING_CANCEL] = (
            self._handle_booking_cancel
        )
        self.operation_handlers[BatchOperationType.BOOKING_SET_DATES] = (
            self._handle_booking_set_dates
        )
        self.operation_handlers[BatchOperationType.ACCOMMODATION_STATUS_UPDATE] = (
            self._handle_accommodation_status_update
        )

        # Compensation handlers
        self.compensation_handlers[BatchOperationType.BOOKING_STATUS_UPDATE] = (
            self._compensate_booking_status_update
        )
        self.compensation_handlers[BatchOperationType.BOOKING_CANCEL] = (
            self._compensate_booking_cancel
        )
        self.compensation_handlers[BatchOperationType.BOOKING_SET_DATES] = (
            self._compensate_booking_set_dates
        )
        self.compensation_handlers[BatchOperationType.ACCOMMODATION_STATUS_UPDATE] = (
            self._compensate_accommodation_status_update
        )

    async def execute_batch(
        self, batch_request: BatchRequest, user_id: Optional[int] = None
    ) -> BatchJobResult:
        """Execute a batch of operations with Saga pattern for transaction safety."""

        job_start_time = datetime.now()
        saga_transaction = SagaTransaction(
            job_id=batch_request.job_id, started_at=job_start_time
        )

        if batch_request.dry_run:
            return await self._execute_dry_run(batch_request, user_id)

        # Validate batch before execution
        validation_result = await self._validate_batch(batch_request)
        if not validation_result.is_valid:
            raise BatchProcessorError(
                f"Batch validation failed: {validation_result.errors}"
            )

        operation_results: List[BatchOperationResult] = []
        successful_operations = 0
        failed_operations = 0

        try:
            # Execute operations in sequence or parallel based on configuration
            if batch_request.parallel_execution:
                operation_results = await self._execute_operations_parallel(
                    batch_request.operations, batch_request, saga_transaction, user_id
                )
            else:
                operation_results = await self._execute_operations_sequential(
                    batch_request.operations, batch_request, saga_transaction, user_id
                )

            # Count successes and failures
            successful_operations = sum(
                1 for result in operation_results if result.success
            )
            failed_operations = sum(
                1 for result in operation_results if not result.success
            )

            # If fail_fast is enabled and we have failures, trigger compensation
            if batch_request.fail_fast and failed_operations > 0:
                logger.warning(
                    f"Batch {batch_request.job_id} failed fast with {failed_operations} failures"
                )
                await self._execute_compensation(saga_transaction, operation_results)
                saga_transaction.status = BatchOperationStatus.FAILED
            else:
                saga_transaction.status = (
                    BatchOperationStatus.COMPLETED
                    if failed_operations == 0
                    else BatchOperationStatus.PARTIALLY_COMPLETED
                )

        except Exception as e:
            logger.error(
                f"Batch execution failed for job {batch_request.job_id}: {str(e)}"
            )

            # Execute compensation for completed operations
            if batch_request.enable_compensation:
                try:
                    await self._execute_compensation(
                        saga_transaction, operation_results
                    )
                except CompensationError as comp_err:
                    logger.error(
                        f"Compensation failed for job {batch_request.job_id}: {str(comp_err)}"
                    )

            saga_transaction.status = BatchOperationStatus.FAILED
            failed_operations = len(operation_results)
            successful_operations = 0

            # Re-raise the original exception
            raise BatchProcessorError(f"Batch execution failed: {str(e)}")

        finally:
            saga_transaction.completed_at = datetime.now()
            # Persist saga transaction state for audit
            await self._persist_saga_transaction(saga_transaction)

        # Create final job result
        job_result = BatchJobResult(
            job_id=batch_request.job_id,
            job_name=batch_request.job_name,
            status=BatchJobStatus.COMPLETED
            if failed_operations == 0
            else (
                BatchJobStatus.FAILED
                if successful_operations == 0
                else BatchJobStatus.COMPLETED
            ),
            started_at=job_start_time,
            completed_at=datetime.now(),
            total_execution_time_ms=int(
                (datetime.now() - job_start_time).total_seconds() * 1000
            ),
            total_operations=len(batch_request.operations),
            successful_operations=successful_operations,
            failed_operations=failed_operations,
            compensated_operations=len(saga_transaction.compensation_operations),
            operation_results=operation_results,
            has_failures=failed_operations > 0,
            failure_summary=self._generate_failure_summary(operation_results)
            if failed_operations > 0
            else None,
            compensation_summary=self._generate_compensation_summary(saga_transaction),
            dry_run=batch_request.dry_run,
            created_by=user_id,
            created_at=job_start_time,
        )

        return job_result

    async def _execute_operations_sequential(
        self,
        operations: List[BatchOperationItem],
        batch_request: BatchRequest,
        saga_transaction: SagaTransaction,
        user_id: Optional[int],
    ) -> List[BatchOperationResult]:
        """Execute operations sequentially."""
        results = []

        for operation in operations:
            if batch_request.fail_fast and any(not r.success for r in results):
                # Skip remaining operations if fail_fast is enabled and we have failures
                break

            result = await self._execute_single_operation(
                operation, batch_request.job_id, user_id, batch_request.dry_run
            )
            results.append(result)

            if result.success:
                saga_transaction.completed_operations.append(operation.operation_id)
            else:
                saga_transaction.failed_operation_id = operation.operation_id
                if batch_request.fail_fast:
                    break

        return results

    async def _execute_operations_parallel(
        self,
        operations: List[BatchOperationItem],
        batch_request: BatchRequest,
        saga_transaction: SagaTransaction,
        user_id: Optional[int],
    ) -> List[BatchOperationResult]:
        """Execute operations in parallel with limited concurrency."""
        # Limit concurrent operations to prevent overwhelming the database
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent operations

        async def execute_with_semaphore(operation):
            async with semaphore:
                return await self._execute_single_operation(
                    operation, batch_request.job_id, user_id, batch_request.dry_run
                )

        # Execute all operations concurrently
        tasks = [execute_with_semaphore(op) for op in operations]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Convert exception to failed operation result
                operation = operations[i]
                failed_result = BatchOperationResult(
                    operation_id=operation.operation_id,
                    target_id=operation.target_id,
                    operation_type=operation.operation_type,
                    status=BatchOperationStatus.FAILED,
                    success=False,
                    error_message=str(result),
                    error_code="EXECUTION_EXCEPTION",
                )
                processed_results.append(failed_result)
            else:
                processed_results.append(result)
                if result.success:
                    saga_transaction.completed_operations.append(result.operation_id)

        return processed_results

    async def _execute_single_operation(
        self,
        operation: BatchOperationItem,
        job_id: str,
        user_id: Optional[int],
        dry_run: bool = False,
    ) -> BatchOperationResult:
        """Execute a single batch operation."""
        start_time = datetime.now()

        context = OperationContext(
            db=self.db,
            operation=operation,
            job_id=job_id,
            user_id=user_id,
            dry_run=dry_run,
        )

        try:
            # Get operation handler
            handler = self.operation_handlers.get(operation.operation_type)
            if not handler:
                raise BatchProcessorError(
                    f"No handler found for operation type: {operation.operation_type}"
                )

            # Capture before state for compensation
            before_state = await self._capture_entity_state(operation)

            # Execute the operation
            await handler(context)

            # Capture after state
            after_state = (
                await self._capture_entity_state(operation) if not dry_run else None
            )

            end_time = datetime.now()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return BatchOperationResult(
                operation_id=operation.operation_id,
                target_id=operation.target_id,
                operation_type=operation.operation_type,
                status=BatchOperationStatus.COMPLETED,
                started_at=start_time,
                completed_at=end_time,
                execution_time_ms=execution_time,
                success=True,
                before_state=before_state,
                after_state=after_state,
            )

        except Exception as e:
            end_time = datetime.now()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            logger.error(f"Operation {operation.operation_id} failed: {str(e)}")

            return BatchOperationResult(
                operation_id=operation.operation_id,
                target_id=operation.target_id,
                operation_type=operation.operation_type,
                status=BatchOperationStatus.FAILED,
                started_at=start_time,
                completed_at=end_time,
                execution_time_ms=execution_time,
                success=False,
                error_message=str(e),
                error_code=type(e).__name__,
            )

    async def _execute_compensation(
        self,
        saga_transaction: SagaTransaction,
        operation_results: List[BatchOperationResult],
    ):
        """Execute compensation operations for completed operations."""
        compensation_operations = []

        # Create compensation operations for successful operations in reverse order
        successful_operations = [r for r in operation_results if r.success]
        for result in reversed(successful_operations):
            compensation_op = CompensationOperation(
                original_operation_id=result.operation_id,
                compensation_type=f"compensate_{result.operation_type.value}",
                compensation_data={
                    "target_id": result.target_id,
                    "before_state": result.before_state,
                    "after_state": result.after_state,
                },
            )
            compensation_operations.append(compensation_op)

        # Execute compensation operations
        saga_transaction.compensation_operations = compensation_operations
        for comp_op in compensation_operations:
            try:
                await self._execute_compensation_operation(comp_op)
                comp_op.status = BatchOperationStatus.COMPLETED
                comp_op.executed_at = datetime.now()
            except Exception as e:
                comp_op.status = BatchOperationStatus.FAILED
                comp_op.error_message = str(e)
                logger.error(
                    f"Compensation operation {comp_op.compensation_id} failed: {str(e)}"
                )

        saga_transaction.compensation_status = BatchOperationStatus.COMPLETED

    async def _execute_compensation_operation(
        self, compensation_op: CompensationOperation
    ):
        """Execute a single compensation operation."""
        # Extract operation type from compensation data
        original_operation_type = BatchOperationType(
            compensation_op.compensation_type.replace("compensate_", "")
        )

        handler = self.compensation_handlers.get(original_operation_type)
        if not handler:
            raise CompensationError(
                f"No compensation handler for operation type: {original_operation_type}"
            )

        await handler(compensation_op)

    # Operation Handlers
    async def _handle_booking_status_update(self, context: OperationContext) -> Any:
        """Handle booking status update operation."""
        from app.models.booking import Booking, BookingStatus

        target_id = context.operation.target_id
        new_status = BookingStatus(context.operation.parameters.get("new_status"))

        if context.dry_run:
            return {
                "action": "update_booking_status",
                "target_id": target_id,
                "new_status": new_status.value,
            }

        # Update booking status
        stmt = update(Booking).where(Booking.id == target_id).values(status=new_status)
        await context.db.execute(stmt)
        await context.db.commit()

        return {"updated_booking_id": target_id, "new_status": new_status.value}

    async def _handle_booking_cancel(self, context: OperationContext) -> Any:
        """Handle booking cancellation operation."""
        from app.models.booking import Booking, BookingStatus

        target_id = context.operation.target_id
        cancellation_reason = context.operation.parameters.get("cancellation_reason")

        if context.dry_run:
            return {
                "action": "cancel_booking",
                "target_id": target_id,
                "reason": cancellation_reason,
            }

        # Cancel booking
        stmt = (
            update(Booking)
            .where(Booking.id == target_id)
            .values(
                status=BookingStatus.CANCELLED,
                comments=f"Cancelled: {cancellation_reason}",
            )
        )
        await context.db.execute(stmt)
        await context.db.commit()

        return {"cancelled_booking_id": target_id, "reason": cancellation_reason}

    async def _handle_booking_set_dates(self, context: OperationContext) -> Any:
        """Handle setting dates on open-date bookings."""
        from app.models.booking import Booking

        target_id = context.operation.target_id
        check_in_date = context.operation.parameters.get("check_in_date")
        check_out_date = context.operation.parameters.get("check_out_date")

        if context.dry_run:
            return {
                "action": "set_booking_dates",
                "target_id": target_id,
                "check_in": check_in_date,
                "check_out": check_out_date,
            }

        # Set booking dates
        stmt = (
            update(Booking)
            .where(Booking.id == target_id)
            .values(
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                is_open_dates=False,
            )
        )
        await context.db.execute(stmt)
        await context.db.commit()

        return {
            "booking_id": target_id,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
        }

    async def _handle_accommodation_status_update(
        self, context: OperationContext
    ) -> Any:
        """Handle accommodation status update operation."""
        from app.models.accommodation import Accommodation, AccommodationStatus

        target_id = context.operation.target_id
        new_status = AccommodationStatus(context.operation.parameters.get("new_status"))

        if context.dry_run:
            return {
                "action": "update_accommodation_status",
                "target_id": target_id,
                "new_status": new_status.value,
            }

        # Update accommodation status
        stmt = (
            update(Accommodation)
            .where(Accommodation.id == target_id)
            .values(status=new_status)
        )
        await context.db.execute(stmt)
        await context.db.commit()

        return {"updated_accommodation_id": target_id, "new_status": new_status.value}

    # Compensation Handlers
    async def _compensate_booking_status_update(
        self, compensation_op: CompensationOperation
    ):
        """Compensate booking status update by restoring original status."""
        from app.models.booking import Booking

        target_id = compensation_op.compensation_data["target_id"]
        original_status = compensation_op.compensation_data["before_state"]["status"]

        stmt = (
            update(Booking)
            .where(Booking.id == target_id)
            .values(status=original_status)
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def _compensate_booking_cancel(self, compensation_op: CompensationOperation):
        """Compensate booking cancellation by restoring original status."""
        from app.models.booking import Booking

        target_id = compensation_op.compensation_data["target_id"]
        before_state = compensation_op.compensation_data["before_state"]

        stmt = (
            update(Booking)
            .where(Booking.id == target_id)
            .values(
                status=before_state["status"], comments=before_state.get("comments")
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def _compensate_booking_set_dates(
        self, compensation_op: CompensationOperation
    ):
        """Compensate date setting by restoring open dates status."""
        from app.models.booking import Booking

        target_id = compensation_op.compensation_data["target_id"]

        stmt = (
            update(Booking)
            .where(Booking.id == target_id)
            .values(check_in_date=None, check_out_date=None, is_open_dates=True)
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def _compensate_accommodation_status_update(
        self, compensation_op: CompensationOperation
    ):
        """Compensate accommodation status update by restoring original status."""
        from app.models.accommodation import Accommodation

        target_id = compensation_op.compensation_data["target_id"]
        original_status = compensation_op.compensation_data["before_state"]["status"]

        stmt = (
            update(Accommodation)
            .where(Accommodation.id == target_id)
            .values(status=original_status)
        )
        await self.db.execute(stmt)
        await self.db.commit()

    # Utility methods
    async def _capture_entity_state(
        self, operation: BatchOperationItem
    ) -> Dict[str, Any]:
        """Capture the current state of an entity for compensation purposes."""
        # This is a simplified implementation - in production, you'd want more sophisticated state capture
        target_id = operation.target_id

        if operation.operation_type in [
            BatchOperationType.BOOKING_STATUS_UPDATE,
            BatchOperationType.BOOKING_CANCEL,
            BatchOperationType.BOOKING_SET_DATES,
        ]:
            from app.models.booking import Booking

            stmt = select(Booking).where(Booking.id == target_id)
            result = await self.db.execute(stmt)
            booking = result.scalar_one_or_none()
            if booking:
                return {
                    "status": booking.status.value,
                    "comments": booking.comments,
                    "check_in_date": booking.check_in_date.isoformat()
                    if booking.check_in_date
                    else None,
                    "check_out_date": booking.check_out_date.isoformat()
                    if booking.check_out_date
                    else None,
                    "is_open_dates": booking.is_open_dates,
                }

        elif operation.operation_type == BatchOperationType.ACCOMMODATION_STATUS_UPDATE:
            from app.models.accommodation import Accommodation

            stmt = select(Accommodation).where(Accommodation.id == target_id)
            result = await self.db.execute(stmt)
            accommodation = result.scalar_one_or_none()
            if accommodation:
                return {
                    "status": accommodation.status.value,
                    "condition": accommodation.condition.value,
                }

        return {}

    async def _validate_batch(
        self, batch_request: BatchRequest
    ) -> BatchValidationResult:
        """Validate batch operations before execution."""
        errors = []
        warnings = []

        for operation in batch_request.operations:
            # Validate operation has required parameters
            if not operation.parameters:
                errors.append(
                    BatchValidationError(
                        operation_id=operation.operation_id,
                        target_id=operation.target_id,
                        error_code="MISSING_PARAMETERS",
                        error_message="Operation parameters are required",
                    )
                )
                continue

            # Validate entity exists
            entity_exists = await self._validate_entity_exists(operation)
            if not entity_exists:
                errors.append(
                    BatchValidationError(
                        operation_id=operation.operation_id,
                        target_id=operation.target_id,
                        error_code="ENTITY_NOT_FOUND",
                        error_message=f"Target entity {operation.target_id} not found",
                    )
                )

        return BatchValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            validated_operations=len(batch_request.operations),
            invalid_operations=len(errors),
        )

    async def _validate_entity_exists(self, operation: BatchOperationItem) -> bool:
        """Validate that the target entity exists."""
        target_id = operation.target_id

        if operation.operation_type in [
            BatchOperationType.BOOKING_STATUS_UPDATE,
            BatchOperationType.BOOKING_CANCEL,
            BatchOperationType.BOOKING_SET_DATES,
        ]:
            from app.models.booking import Booking

            stmt = select(Booking.id).where(Booking.id == target_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none() is not None

        elif operation.operation_type == BatchOperationType.ACCOMMODATION_STATUS_UPDATE:
            from app.models.accommodation import Accommodation

            stmt = select(Accommodation.id).where(Accommodation.id == target_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none() is not None

        return False

    async def _execute_dry_run(
        self, batch_request: BatchRequest, user_id: Optional[int]
    ) -> BatchJobResult:
        """Execute a dry run to preview batch operation effects."""
        start_time = datetime.now()

        # Execute operations in dry-run mode
        operation_results = []
        for operation in batch_request.operations:
            result = await self._execute_single_operation(
                operation, batch_request.job_id, user_id, dry_run=True
            )
            operation_results.append(result)

        return BatchJobResult(
            job_id=batch_request.job_id,
            job_name=f"DRY RUN: {batch_request.job_name}",
            status=BatchJobStatus.COMPLETED,
            started_at=start_time,
            completed_at=datetime.now(),
            total_execution_time_ms=int(
                (datetime.now() - start_time).total_seconds() * 1000
            ),
            total_operations=len(batch_request.operations),
            successful_operations=len(operation_results),
            failed_operations=0,
            compensated_operations=0,
            operation_results=operation_results,
            has_failures=False,
            dry_run=True,
            created_by=user_id,
            created_at=start_time,
        )

    async def _persist_saga_transaction(self, saga_transaction: SagaTransaction):
        """Persist saga transaction state for audit purposes."""
        # In a production system, you'd persist this to a dedicated audit table
        # For now, we'll just log it
        logger.info(f"Saga transaction completed: {saga_transaction.transaction_id}")

    def _generate_failure_summary(
        self, operation_results: List[BatchOperationResult]
    ) -> str:
        """Generate a summary of failures."""
        failed_results = [r for r in operation_results if not r.success]
        failure_counts = {}

        for result in failed_results:
            error_code = result.error_code or "UNKNOWN_ERROR"
            failure_counts[error_code] = failure_counts.get(error_code, 0) + 1

        summary_parts = []
        for error_code, count in failure_counts.items():
            summary_parts.append(f"{error_code}: {count}")

        return f"{len(failed_results)} operations failed. Breakdown: {', '.join(summary_parts)}"

    def _generate_compensation_summary(self, saga_transaction: SagaTransaction) -> str:
        """Generate a summary of compensation operations."""
        if not saga_transaction.compensation_operations:
            return "No compensation required"

        successful_compensations = sum(
            1
            for op in saga_transaction.compensation_operations
            if op.status == BatchOperationStatus.COMPLETED
        )
        failed_compensations = sum(
            1
            for op in saga_transaction.compensation_operations
            if op.status == BatchOperationStatus.FAILED
        )

        return f"Compensation: {successful_compensations} successful, {failed_compensations} failed"
