from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, validator

from app.models.accommodation import AccommodationCondition, AccommodationStatus
from app.models.booking import BookingStatus


class BatchOperationType(str, Enum):
    """Types of batch operations supported."""

    BOOKING_STATUS_UPDATE = "booking_status_update"
    BOOKING_CANCEL = "booking_cancel"
    BOOKING_SET_DATES = "booking_set_dates"
    BOOKING_PAYMENT_ADD = "booking_payment_add"
    ACCOMMODATION_STATUS_UPDATE = "accommodation_status_update"
    CLIENT_UPDATE = "client_update"
    INVENTORY_ASSIGN = "inventory_assign"
    CUSTOM_ITEM_ADD = "custom_item_add"


class BatchOperationStatus(str, Enum):
    """Status of batch operations."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"
    CANCELLED = "cancelled"


class BatchJobStatus(str, Enum):
    """Overall batch job status."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchOperationItem(BaseModel):
    """Individual operation within a batch."""

    operation_id: str = Field(default_factory=lambda: str(uuid4()))
    target_id: int = Field(description="ID of the target entity")
    operation_type: BatchOperationType
    parameters: Dict[str, Any] = Field(description="Operation-specific parameters")

    # Execution tracking
    status: BatchOperationStatus = BatchOperationStatus.PENDING
    error_message: Optional[str] = None
    executed_at: Optional[datetime] = None
    compensated_at: Optional[datetime] = None


class BookingStatusUpdateOperation(BaseModel):
    """Batch operation for updating booking statuses."""

    booking_ids: List[int] = Field(..., min_items=1)
    new_status: BookingStatus
    reason: Optional[str] = Field(None, description="Reason for status change")
    notify_clients: bool = Field(default=False, description="Whether to notify clients")


class BookingCancelOperation(BaseModel):
    """Batch operation for cancelling bookings."""

    booking_ids: List[int] = Field(..., min_items=1)
    cancellation_reason: str = Field(..., min_length=1)
    refund_amount: Optional[float] = Field(None, ge=0)
    notify_clients: bool = Field(default=True, description="Whether to notify clients")


class BookingSetDatesOperation(BaseModel):
    """Batch operation for setting dates on open-date bookings."""

    booking_date_assignments: List[Dict[str, Any]] = Field(
        ..., description="List of {booking_id, check_in_date, check_out_date}"
    )
    validate_availability: bool = Field(
        default=True, description="Whether to validate availability"
    )

    @validator("booking_date_assignments")
    def validate_date_assignments(cls, v):
        for assignment in v:
            required_fields = {"booking_id", "check_in_date", "check_out_date"}
            if not all(field in assignment for field in required_fields):
                raise ValueError(f"Each assignment must have: {required_fields}")
        return v


class AccommodationStatusUpdateOperation(BaseModel):
    """Batch operation for updating accommodation statuses."""

    accommodation_ids: List[int] = Field(..., min_items=1)
    new_status: AccommodationStatus
    new_condition: Optional[AccommodationCondition] = None
    reason: Optional[str] = Field(None, description="Reason for status change")
    maintenance_notes: Optional[str] = None


class BatchRequest(BaseModel):
    """Main batch operation request."""

    job_id: str = Field(default_factory=lambda: str(uuid4()))
    job_name: str = Field(..., min_length=1, description="Human-readable job name")
    description: Optional[str] = Field(None, description="Job description")

    operations: List[BatchOperationItem] = Field(..., min_items=1)

    # Execution settings
    dry_run: bool = Field(default=False, description="Whether to perform a dry run")
    fail_fast: bool = Field(
        default=False, description="Whether to stop on first failure"
    )
    parallel_execution: bool = Field(
        default=False, description="Whether to execute operations in parallel"
    )

    # Saga pattern settings
    enable_compensation: bool = Field(
        default=True, description="Whether to enable compensation on failure"
    )
    compensation_timeout_seconds: int = Field(
        default=300, description="Timeout for compensation operations"
    )

    # Scheduling
    execute_at: Optional[datetime] = Field(
        None, description="When to execute the batch (if scheduled)"
    )

    @validator("operations")
    def validate_operations(cls, v):
        if len(v) > 1000:  # Reasonable limit
            raise ValueError("Maximum 1000 operations per batch")
        return v


class BatchOperationResult(BaseModel):
    """Result of a single batch operation."""

    operation_id: str
    target_id: int
    operation_type: BatchOperationType
    status: BatchOperationStatus

    # Execution details
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_ms: Optional[int] = None

    # Results
    success: bool
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    warning_messages: List[str] = Field(default_factory=list)

    # Data changes
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None

    # Compensation details
    compensation_operation_id: Optional[str] = None
    compensated: bool = False
    compensation_error: Optional[str] = None


class BatchJobResult(BaseModel):
    """Complete result of a batch job."""

    job_id: str
    job_name: str
    status: BatchJobStatus

    # Execution summary
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_execution_time_ms: Optional[int] = None

    # Operation statistics
    total_operations: int
    successful_operations: int
    failed_operations: int
    compensated_operations: int

    # Detailed results
    operation_results: List[BatchOperationResult]

    # Overall error handling
    has_failures: bool
    failure_summary: Optional[str] = None
    compensation_summary: Optional[str] = None

    # Metadata
    dry_run: bool
    created_by: Optional[int] = None  # User ID
    created_at: datetime


class BatchJobInfo(BaseModel):
    """Basic information about a batch job."""

    job_id: str
    job_name: str
    status: BatchJobStatus
    total_operations: int
    successful_operations: int = 0
    failed_operations: int = 0
    progress_percentage: float = 0.0

    created_at: datetime
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None

    created_by: Optional[int] = None


class BatchJobListResponse(BaseModel):
    """Response for listing batch jobs."""

    jobs: List[BatchJobInfo]
    pagination: Dict[str, Any]


class DryRunResult(BaseModel):
    """Result of a dry run execution."""

    job_id: str
    validation_results: List[Dict[str, Any]]
    estimated_execution_time_seconds: int
    potential_conflicts: List[str]
    warnings: List[str]
    can_proceed: bool

    # Preview of changes
    affected_entities: Dict[str, List[int]]  # entity_type -> [ids]
    estimated_changes: Dict[str, Any]


class BatchValidationError(BaseModel):
    """Validation error for batch operations."""

    operation_id: str
    target_id: int
    error_code: str
    error_message: str
    field_errors: Optional[Dict[str, str]] = None


class BatchValidationResult(BaseModel):
    """Result of batch operation validation."""

    is_valid: bool
    errors: List[BatchValidationError] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validated_operations: int
    invalid_operations: int


class CompensationOperation(BaseModel):
    """Compensation operation for Saga pattern."""

    compensation_id: str = Field(default_factory=lambda: str(uuid4()))
    original_operation_id: str
    compensation_type: str
    compensation_data: Dict[str, Any]

    status: BatchOperationStatus = BatchOperationStatus.PENDING
    executed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class SagaTransaction(BaseModel):
    """Saga transaction for batch operations."""

    transaction_id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: str

    # Transaction state
    status: BatchOperationStatus = BatchOperationStatus.PENDING
    completed_operations: List[str] = Field(default_factory=list)
    failed_operation_id: Optional[str] = None

    # Compensation tracking
    compensation_operations: List[CompensationOperation] = Field(default_factory=list)
    compensation_status: BatchOperationStatus = BatchOperationStatus.PENDING

    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# Specialized batch operation schemas for specific business operations


class BulkBookingConfirmation(BaseModel):
    """Bulk booking confirmation with payment validation."""

    booking_ids: List[int] = Field(..., min_items=1)
    require_full_payment: bool = Field(default=False)
    send_confirmation_emails: bool = Field(default=True)
    confirmation_message: Optional[str] = None


class BulkInventoryAssignment(BaseModel):
    """Bulk inventory assignment to bookings."""

    assignments: List[Dict[str, Any]] = Field(
        ..., description="List of {booking_id, inventory_item_ids}"
    )
    validate_availability: bool = Field(default=True)
    override_conflicts: bool = Field(default=False)


class BulkDateAssignment(BaseModel):
    """Bulk date assignment for open-date bookings."""

    assignments: List[Dict[str, Any]] = Field(
        ...,
        description="List of {booking_id, check_in_date, check_out_date, accommodation_id?}",
    )
    validate_accommodation_availability: bool = Field(default=True)
    auto_assign_accommodations: bool = Field(default=False)
    preferred_accommodation_types: Optional[List[int]] = None


class BatchProgressUpdate(BaseModel):
    """Progress update for long-running batch operations."""

    job_id: str
    current_operation: int
    total_operations: int
    progress_percentage: float
    estimated_time_remaining_seconds: Optional[int] = None
    current_operation_description: str

    # Real-time statistics
    operations_per_second: float
    successful_operations: int
    failed_operations: int
