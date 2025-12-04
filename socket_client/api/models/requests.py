"""
Pydantic request models for API endpoints.
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class StreamsUpdate(BaseModel):
    """Request model for updating WebSocket stream subscriptions."""

    streams: list[str] = Field(
        ..., description="List of Binance WebSocket streams (e.g., 'btcusdt@trade')"
    )
    changed_by: str = Field(..., description="Who is making this change")
    reason: Optional[str] = Field(None, description="Reason for the change")
    validate_only: bool = Field(
        False, description="If true, only validate parameters without saving"
    )


class ReconnectionUpdate(BaseModel):
    """Request model for updating reconnection parameters."""

    reconnect_delay: int = Field(
        ..., ge=1, le=300, description="Initial reconnection delay in seconds"
    )
    max_reconnect_attempts: int = Field(
        ..., ge=1, le=100, description="Maximum reconnection attempts"
    )
    backoff_multiplier: float = Field(
        2.0, ge=1.0, le=10.0, description="Exponential backoff multiplier"
    )
    changed_by: str = Field(..., description="Who is making this change")
    reason: Optional[str] = Field(None, description="Reason for the change")
    validate_only: bool = Field(
        False, description="If true, only validate parameters without saving"
    )


class CircuitBreakerUpdate(BaseModel):
    """Request model for updating circuit breaker parameters."""

    failure_threshold: int = Field(
        ..., ge=1, le=50, description="Number of failures before opening circuit"
    )
    recovery_timeout: int = Field(
        ..., ge=10, le=600, description="Recovery timeout in seconds"
    )
    half_open_max_calls: int = Field(
        3, ge=1, le=10, description="Max calls in half-open state"
    )
    changed_by: str = Field(..., description="Who is making this change")
    reason: Optional[str] = Field(None, description="Reason for the change")
    validate_only: bool = Field(
        False, description="If true, only validate parameters without saving"
    )


class ConfigValidationRequest(BaseModel):
    """Request model for configuration validation."""

    config_type: Literal["streams", "reconnection", "circuit_breaker"] = Field(
        ..., description="Type of configuration to validate"
    )
    parameters: dict[str, Any] = Field(
        ..., description="Configuration parameters to validate"
    )
