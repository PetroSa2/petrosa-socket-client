"""Socket-client subsystem evaluator (P2.7, petrosa_k8s#697 AC1 / socket-client#123).

Adopts the shared `petrosa_otel.evaluators` framework (P2.1) so socket-client
publishes a structured health verdict on ``evaluator.socket-client.verdict``,
closing one of the five "silent service" gaps that keep FR17 / FR23 / FR32 at
YELLOW.
"""

from socket_client.evaluators.health_evaluator import (
    SocketClientHealthEvaluator,
    build_socket_client_health_evaluator,
)

__all__ = [
    "SocketClientHealthEvaluator",
    "build_socket_client_health_evaluator",
]
