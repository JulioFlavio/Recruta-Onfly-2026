"""Conversão de uma linha do CSV para o modelo de reserva."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from ..exceptions import InputFileError
from ..models import RawRow, Reservation
from .status_policy import VALID_STATUSES


class RowParser:
    """Converte a linha crua em Reservation.

    O arquivo de entrada é consistente; falhas de formato são erro de arquivo, não dado a
    ser descartado.
    """

    def parse(self, raw: RawRow) -> Reservation:
        values = raw.values

        def text(column: str) -> str:
            return (values.get(column) or "").strip()

        try:
            reservation = Reservation(
                reservation_id=text("reservation_id"),
                traveler_name=text("traveler_name"),
                company_id=text("company_id"),
                hotel_id=text("hotel_id"),
                hotel_name=text("hotel_name"),
                city=text("city"),
                country=text("country"),
                checkin=date.fromisoformat(text("checkin_date")),
                checkout=date.fromisoformat(text("checkout_date")),
                rooms=int(text("rooms")),
                status=text("status").upper(),
                currency=text("currency").upper(),
                amount=Decimal(text("amount")),
                payment_method=text("payment_method"),
                line_number=raw.line_number,
            )
        except (ValueError, InvalidOperation) as err:
            raise InputFileError(f"linha {raw.line_number} inválida: {err}") from err

        problem = self._find_problem(reservation)
        if problem:
            raise InputFileError(f"linha {raw.line_number} inválida: {problem}")
        return reservation

    @staticmethod
    def _find_problem(reservation: Reservation) -> str | None:
        """Regras de consistência que o tipo sozinho não garante."""
        if reservation.status not in VALID_STATUSES:
            return f"status desconhecido {reservation.status!r} (esperado: {', '.join(sorted(VALID_STATUSES))})"
        if not reservation.hotel_id:
            return "hotel_id vazio"
        if not reservation.currency:
            return "currency vazia"
        if reservation.checkout <= reservation.checkin:
            return f"checkout ({reservation.checkout}) deve ser posterior ao checkin ({reservation.checkin})"
        if reservation.rooms < 1:
            return f"rooms deve ser >= 1 (recebido {reservation.rooms})"
        if not reservation.amount.is_finite() or reservation.amount < 0:
            return f"amount deve ser um número >= 0 (recebido {reservation.amount})"
        return None
