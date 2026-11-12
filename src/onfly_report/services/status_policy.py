"""Política de status das reservas."""

from __future__ import annotations

CONFIRMED = "CONFIRMED"
CANCELLED = "CANCELLED"
NO_SHOW = "NO_SHOW"

VALID_STATUSES = frozenset({CONFIRMED, CANCELLED, NO_SHOW})


def is_billable(status: str) -> bool:
    """Indica se a reserva entra nos totais financeiros e de noites."""
    return status == CONFIRMED
