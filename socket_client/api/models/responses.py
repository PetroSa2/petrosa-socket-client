"""
Pydantic response models for API endpoints.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    """Standard API response wrapper."""

    success: bool = Field(..., description="Whether operation succeeded")
    data: Optional[Any] = Field(None, description="Response data")
    error: Optional[dict[str, Any]] = Field(None, description="Error details if failed")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata")


class StreamsInfo(BaseModel):
    """Streams configuration information."""

    streams: list[str] = Field(..., description="List of subscribed streams")
    count: int = Field(..., description="Number of streams")


class ReconnectionInfo(BaseModel):
    """Reconnection configuration information."""

    reconnect_delay: int = Field(
        ..., description="Initial reconnection delay (seconds)"
    )
    max_reconnect_attempts: int = Field(
        ..., description="Maximum reconnection attempts"
    )
    backoff_multiplier: float = Field(..., description="Exponential backoff multiplier")


class CircuitBreakerInfo(BaseModel):
    """Circuit breaker configuration information."""

    failure_threshold: int = Field(..., description="Failure threshold")
    recovery_timeout: int = Field(..., description="Recovery timeout (seconds)")
    half_open_max_calls: int = Field(..., description="Max calls in half-open state")


class ValidationError(BaseModel):
    """Standardized validation error format."""

    field: str = Field(..., description="Parameter name that failed validation")
    message: str = Field(..., description="Human-readable error message")
    code: str = Field(
        ..., description="Error code (e.g., 'INVALID_TYPE', 'OUT_OF_RANGE')"
    )
    suggested_value: Optional[Any] = Field(
        None, description="Suggested correct value if applicable"
    )


class CrossServiceConflict(BaseModel):
    """Cross-service configuration conflict."""

    service: str = Field(..., description="Service name with conflicting configuration")
    conflict_type: str = Field(
        ..., description="Type of conflict (e.g., 'PARAMETER_CONFLICT')"
    )
    description: str = Field(..., description="Description of the conflict")
    resolution: Optional[str] = Field(
        None, description="Suggested resolution for the conflict"
    )


class ValidationResponse(BaseModel):
    """Standardized validation response across all services."""

    validation_passed: bool = Field(..., description="Whether validation passed")
    errors: list[ValidationError] = Field(
        default_factory=list, description="List of validation errors"
    )
    warnings: list[str] = Field(
        default_factory=list, description="List of validation warnings"
    )
    suggested_fixes: list[str] = Field(
        default_factory=list, description="Suggested fixes for validation errors"
    )
    estimated_impact: dict[str, Any] = Field(
        default_factory=dict, description="Estimated impact of the configuration change"
    )
    conflicts: list[CrossServiceConflict] = Field(
        default_factory=list, description="Cross-service configuration conflicts"
    )
