"""
Configuration management API routes for Socket Client.

Provides endpoints for managing streams, reconnection, and circuit breaker settings.
"""

import logging

from fastapi import APIRouter

from socket_client.api.models.requests import (
    CircuitBreakerUpdate,
    ConfigValidationRequest,
    ReconnectionUpdate,
    StreamsUpdate,
)
from socket_client.api.models.responses import (
    APIResponse,
    CircuitBreakerInfo,
    CrossServiceConflict,
    ReconnectionInfo,
    StreamsInfo,
    ValidationError,
    ValidationResponse,
)
from socket_client.services.config_manager import get_config_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["Configuration"])

# Per #133: the mutation endpoints below (POST streams/reconnection/
# circuit-breaker) previously reported `"success": true` while only ever
# touching a process-local `ConfigManager` attribute in *this* API process —
# a separate process from the running `BinanceWebSocketClient` (see
# socket_client/main.py). There was no persistence layer and no IPC/notify
# path to the WebSocket client, so the mutation was pure fiction.
#
# Rather than silently pretend a durable, propagated change happened, these
# endpoints are now explicit read-only: streams / reconnection / circuit
# breaker parameters are static-at-deploy-time, controlled by env vars /
# the k8s ConfigMap (see constants.py and k8s/socket-client/configmap.yaml),
# and require a pod restart to take effect. `validate_only` requests still
# work (they never claimed to persist anything).
_READ_ONLY_MESSAGE = (
    "This configuration is read-only at runtime (static-at-deploy-time). "
    "Set the corresponding environment variable / k8s ConfigMap value and "
    "restart the service to apply changes. Use validate_only=true to check "
    "parameters without attempting to apply them."
)


def _read_only_response(current: dict, **extra_metadata: object) -> APIResponse:
    """Build the standard NOT_IMPLEMENTED envelope for mutation endpoints."""
    metadata: dict = {"current_config": current}
    metadata.update(extra_metadata)
    return APIResponse(
        success=False,
        data=None,
        error={
            "code": "NOT_IMPLEMENTED",
            "message": _READ_ONLY_MESSAGE,
        },
        metadata=metadata,
    )


def validate_stream_format(stream: str) -> bool:
    """Validate Binance WebSocket stream format."""
    # Basic validation: should be in format symbol@type or symbol@type@interval
    parts = stream.split("@")
    if len(parts) < 2:
        return False
    # Symbol should be lowercase
    if not parts[0].islower():
        return False
    return True


@router.get("/streams", response_model=APIResponse)
async def get_streams():
    """
    Get currently subscribed WebSocket streams.

    **For LLM Agents**: See what streams are currently active.
    """
    try:
        config_manager = get_config_manager()
        streams = config_manager.get_streams()

        return APIResponse(
            success=True,
            data=StreamsInfo(streams=streams, count=len(streams)),
        )
    except Exception as e:
        logger.error(f"Error getting streams: {e}")
        return APIResponse(
            success=False,
            error={"code": "INTERNAL_ERROR", "message": str(e)},
        )


@router.post("/streams", response_model=APIResponse)
async def update_streams(request: StreamsUpdate):
    """
    Validate WebSocket stream subscriptions (read-only endpoint — see #133).

    **Streams are static-at-deploy-time**: set via the `BINANCE_STREAMS` env
    var / k8s ConfigMap and require a pod restart. This endpoint no longer
    claims to apply changes at runtime — it validates format only.

    **Dry Run**: Set `validate_only: true` to test streams without applying
    (this is now the only supported mode; `validate_only: false` returns a
    501-equivalent NOT_IMPLEMENTED envelope).

    Example: POST /api/v1/config/streams
    {
      "streams": ["btcusdt@trade", "ethusdt@ticker"],
      "changed_by": "llm_agent",
      "reason": "Focus on BTC and ETH",
      "validate_only": true
    }
    """
    try:
        # Validate streams
        for stream in request.streams:
            if not validate_stream_format(stream):
                if request.validate_only:
                    return APIResponse(
                        success=True,
                        data=None,
                        metadata={
                            "validation": "failed",
                            "message": f"Invalid stream format: {stream} (validate_only=true)",
                        },
                    )
                return APIResponse(
                    success=False,
                    error={
                        "code": "VALIDATION_ERROR",
                        "message": f"Invalid stream format: {stream}",
                    },
                )

        # If validate_only, return early without saving
        if request.validate_only:
            return APIResponse(
                success=True,
                data=None,
                metadata={
                    "validation": "passed",
                    "message": "Streams are valid but not saved (validate_only=true)",
                    "streams": request.streams,
                    "count": len(request.streams),
                    "changed_by": request.changed_by,
                    "reason": request.reason,
                },
            )

        # Per #133: no runtime mutation path exists to the separate
        # BinanceWebSocketClient process — do not pretend otherwise.
        config_manager = get_config_manager()
        current_streams = config_manager.get_streams()
        return _read_only_response(
            {"streams": current_streams, "count": len(current_streams)},
            requested_streams=request.streams,
            changed_by=request.changed_by,
            reason=request.reason,
        )
    except Exception as e:
        logger.error(f"Error updating streams: {e}")
        return APIResponse(
            success=False,
            error={"code": "INTERNAL_ERROR", "message": str(e)},
        )


@router.get("/reconnection", response_model=APIResponse)
async def get_reconnection():
    """Get reconnection configuration."""
    try:
        config_manager = get_config_manager()
        config = config_manager.get_reconnection_config()

        return APIResponse(
            success=True,
            data=ReconnectionInfo(**config),
        )
    except Exception as e:
        logger.error(f"Error getting reconnection config: {e}")
        return APIResponse(
            success=False,
            error={"code": "INTERNAL_ERROR", "message": str(e)},
        )


@router.post("/reconnection", response_model=APIResponse)
async def update_reconnection(request: ReconnectionUpdate):
    """
    Validate reconnection parameters (read-only endpoint — see #133).

    **Reconnection settings are static-at-deploy-time**: set via
    `WEBSOCKET_RECONNECT_DELAY`/`_MAX_RECONNECT_ATTEMPTS`/`_BACKOFF_MULTIPLIER`
    env vars / the k8s ConfigMap, and require a pod restart. This endpoint no
    longer claims to apply changes at runtime.

    **Dry Run**: Set `validate_only: true` to test parameters (the only
    supported mode; `validate_only: false` returns NOT_IMPLEMENTED).
    """
    try:
        # If validate_only, return early without saving
        if request.validate_only:
            return APIResponse(
                success=True,
                data=None,
                metadata={
                    "validation": "passed",
                    "message": "Reconnection config is valid but not saved (validate_only=true)",
                    "reconnect_delay": request.reconnect_delay,
                    "max_reconnect_attempts": request.max_reconnect_attempts,
                    "backoff_multiplier": request.backoff_multiplier,
                    "changed_by": request.changed_by,
                    "reason": request.reason,
                },
            )

        # Per #133: no runtime mutation path exists — do not pretend otherwise.
        config_manager = get_config_manager()
        return _read_only_response(
            config_manager.get_reconnection_config(),
            requested_reconnect_delay=request.reconnect_delay,
            requested_max_reconnect_attempts=request.max_reconnect_attempts,
            requested_backoff_multiplier=request.backoff_multiplier,
            changed_by=request.changed_by,
            reason=request.reason,
        )
    except Exception as e:
        logger.error(f"Error updating reconnection config: {e}")
        return APIResponse(
            success=False,
            error={"code": "INTERNAL_ERROR", "message": str(e)},
        )


@router.get("/circuit-breaker", response_model=APIResponse)
async def get_circuit_breaker():
    """Get circuit breaker configuration."""
    try:
        config_manager = get_config_manager()
        config = config_manager.get_circuit_breaker_config()

        return APIResponse(
            success=True,
            data=CircuitBreakerInfo(**config),
        )
    except Exception as e:
        logger.error(f"Error getting circuit breaker config: {e}")
        return APIResponse(
            success=False,
            error={"code": "INTERNAL_ERROR", "message": str(e)},
        )


@router.post("/circuit-breaker", response_model=APIResponse)
async def update_circuit_breaker(request: CircuitBreakerUpdate):
    """
    Validate circuit breaker parameters (read-only endpoint — see #133).

    **Circuit breaker settings are static-at-deploy-time**: set via
    `CIRCUIT_BREAKER_FAILURE_THRESHOLD`/`_RECOVERY_TIMEOUT`/
    `_HALF_OPEN_MAX_CALLS` env vars / the k8s ConfigMap, and require a pod
    restart. This endpoint no longer claims to apply changes at runtime.

    **Dry Run**: Set `validate_only: true` to test parameters (the only
    supported mode; `validate_only: false` returns NOT_IMPLEMENTED).
    """
    try:
        # If validate_only, return early without saving
        if request.validate_only:
            return APIResponse(
                success=True,
                data=None,
                metadata={
                    "validation": "passed",
                    "message": "Circuit breaker config is valid but not saved (validate_only=true)",
                    "failure_threshold": request.failure_threshold,
                    "recovery_timeout": request.recovery_timeout,
                    "half_open_max_calls": request.half_open_max_calls,
                    "changed_by": request.changed_by,
                    "reason": request.reason,
                },
            )

        # Per #133: no runtime mutation path exists — do not pretend otherwise.
        config_manager = get_config_manager()
        return _read_only_response(
            config_manager.get_circuit_breaker_config(),
            requested_failure_threshold=request.failure_threshold,
            requested_recovery_timeout=request.recovery_timeout,
            requested_half_open_max_calls=request.half_open_max_calls,
            changed_by=request.changed_by,
            reason=request.reason,
        )
    except Exception as e:
        logger.error(f"Error updating circuit breaker config: {e}")
        return APIResponse(
            success=False,
            error={"code": "INTERNAL_ERROR", "message": str(e)},
        )


@router.post("/validate", response_model=APIResponse)
async def validate_config(request: ConfigValidationRequest):
    """
    Validate configuration without applying changes.

    **For LLM Agents**: Validate configuration parameters before applying them.

    This endpoint performs comprehensive validation including:
    - Parameter type and constraint validation
    - Format validation (stream formats)
    - Range validation (timeouts, thresholds)
    - Dependency validation

    **Example Request**:
    ```json
    {
      "config_type": "streams",
      "parameters": {
        "streams": ["btcusdt@trade", "ethusdt@ticker"]
      }
    }
    ```

    **Example Response**:
    ```json
    {
      "success": true,
      "data": {
        "validation_passed": true,
        "errors": [],
        "warnings": [],
        "suggested_fixes": [],
        "estimated_impact": {
          "risk_level": "low",
          "affected_scope": "streams"
        },
        "conflicts": []
      }
    }
    ```
    """
    try:
        validation_errors = []
        warnings = []
        suggested_fixes = []
        estimated_impact = {}

        # Validate based on config type
        if request.config_type == "streams":
            streams = request.parameters.get("streams", [])
            if not isinstance(streams, list):
                validation_errors.append(
                    ValidationError(
                        field="streams",
                        message="Streams must be a list",
                        code="INVALID_TYPE",
                        suggested_value=[],
                    )
                )
            else:
                for stream in streams:
                    if not isinstance(stream, str):
                        validation_errors.append(
                            ValidationError(
                                field="streams",
                                message=f"Stream must be a string, got {type(stream).__name__}",
                                code="INVALID_TYPE",
                                suggested_value=str(stream),
                            )
                        )
                    elif not validate_stream_format(stream):
                        validation_errors.append(
                            ValidationError(
                                field="streams",
                                message=f"Invalid stream format: {stream}",
                                code="INVALID_FORMAT",
                                suggested_value=stream.lower() if stream else None,
                            )
                        )

            estimated_impact = {
                "risk_level": "low",
                "affected_scope": f"{len(streams)} streams",
                "message": "Changing streams will affect WebSocket subscriptions",
            }

        elif request.config_type == "reconnection":
            reconnect_delay = request.parameters.get("reconnect_delay")
            max_reconnect_attempts = request.parameters.get("max_reconnect_attempts")

            if reconnect_delay is not None:
                if not isinstance(reconnect_delay, int):
                    validation_errors.append(
                        ValidationError(
                            field="reconnect_delay",
                            message="Must be an integer",
                            code="INVALID_TYPE",
                            suggested_value=5,
                        )
                    )
                elif reconnect_delay < 1 or reconnect_delay > 300:
                    validation_errors.append(
                        ValidationError(
                            field="reconnect_delay",
                            message="Must be between 1 and 300 seconds",
                            code="OUT_OF_RANGE",
                            suggested_value=5,
                        )
                    )

            if max_reconnect_attempts is not None:
                if not isinstance(max_reconnect_attempts, int):
                    validation_errors.append(
                        ValidationError(
                            field="max_reconnect_attempts",
                            message="Must be an integer",
                            code="INVALID_TYPE",
                            suggested_value=10,
                        )
                    )
                elif max_reconnect_attempts < 1 or max_reconnect_attempts > 100:
                    validation_errors.append(
                        ValidationError(
                            field="max_reconnect_attempts",
                            message="Must be between 1 and 100",
                            code="OUT_OF_RANGE",
                            suggested_value=10,
                        )
                    )

            estimated_impact = {
                "risk_level": "low",
                "affected_scope": "reconnection behavior",
                "message": "Changing reconnection config affects connection reliability",
            }

        elif request.config_type == "circuit_breaker":
            failure_threshold = request.parameters.get("failure_threshold")
            recovery_timeout = request.parameters.get("recovery_timeout")

            if failure_threshold is not None:
                if not isinstance(failure_threshold, int):
                    validation_errors.append(
                        ValidationError(
                            field="failure_threshold",
                            message="Must be an integer",
                            code="INVALID_TYPE",
                            suggested_value=5,
                        )
                    )
                elif failure_threshold < 1 or failure_threshold > 50:
                    validation_errors.append(
                        ValidationError(
                            field="failure_threshold",
                            message="Must be between 1 and 50",
                            code="OUT_OF_RANGE",
                            suggested_value=5,
                        )
                    )

            if recovery_timeout is not None:
                if not isinstance(recovery_timeout, int):
                    validation_errors.append(
                        ValidationError(
                            field="recovery_timeout",
                            message="Must be an integer",
                            code="INVALID_TYPE",
                            suggested_value=60,
                        )
                    )
                elif recovery_timeout < 10 or recovery_timeout > 600:
                    validation_errors.append(
                        ValidationError(
                            field="recovery_timeout",
                            message="Must be between 10 and 600 seconds",
                            code="OUT_OF_RANGE",
                            suggested_value=60,
                        )
                    )

            estimated_impact = {
                "risk_level": "medium",
                "affected_scope": "circuit breaker behavior",
                "message": "Changing circuit breaker config affects error handling",
            }

        else:
            validation_errors.append(
                ValidationError(
                    field="config_type",
                    message=f"Unknown config type: {request.config_type}",
                    code="INVALID_VALUE",
                    suggested_value="streams",
                )
            )

        # Generate suggested fixes
        for error in validation_errors:
            if error.suggested_value is not None:
                suggested_fixes.append(f"Set {error.field} to {error.suggested_value}")

        # Cross-service conflict detection (simplified - no conflicts for socket-client)
        conflicts: list[CrossServiceConflict] = []

        validation_response = ValidationResponse(
            validation_passed=len(validation_errors) == 0,
            errors=validation_errors,
            warnings=warnings,
            suggested_fixes=suggested_fixes,
            estimated_impact=estimated_impact,
            conflicts=conflicts,
        )

        return APIResponse(
            success=True,
            data=validation_response,
            metadata={
                "validation_mode": "dry_run",
                "config_type": request.config_type,
            },
        )

    except Exception as e:
        logger.error(f"Error validating config: {e}")
        return APIResponse(
            success=False,
            error={"code": "INTERNAL_ERROR", "message": str(e)},
        )
