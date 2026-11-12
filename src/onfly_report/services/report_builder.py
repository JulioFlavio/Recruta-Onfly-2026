"""Construção do relatório consolidado."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from ..exceptions import InputFileError, UnknownCurrencyError
from ..models import Reservation
from ..repositories.csv_rate_repository import CsvRateRepository
from ..repositories.csv_reservation_repository import CsvReservationRepository
from .currency_converter import convert_to_brl
from .row_parser import RowParser
from .status_policy import CANCELLED, CONFIRMED, NO_SHOW, is_billable
from .stay_calculator import calculate_room_nights

logger = logging.getLogger(__name__)

REPORT_VERSION = "1.0"
MONEY_QUANTUM = Decimal("0.01")
FIXED_OFFSET = timezone(timedelta(hours=-3))


def format_money(value: Decimal) -> str:
    """Serializa dinheiro com duas casas, arredondamento half-up."""
    return str(value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP))


@dataclass
class _Bucket:
    """Acumulador de reservas faturáveis (valores exatos, sem arredondamento)."""

    reservations: int = 0
    room_nights: int = 0
    amount: Decimal = field(default_factory=Decimal)

    def add(self, room_nights: int, amount: Decimal) -> None:
        self.reservations += 1
        self.room_nights += room_nights
        self.amount += amount


@dataclass
class _HotelBucket(_Bucket):
    hotel_name: str = ""


class ReportBuilder:
    """Orquestra leitura, conversão e agregação em uma única passada pelo arquivo."""

    def __init__(
        self,
        reservation_repository: CsvReservationRepository,
        rate_repository: CsvRateRepository,
        top_n: int = 5,
        now: datetime | None = None,
    ) -> None:
        self._reservation_repository = reservation_repository
        self._rate_repository = rate_repository
        self._top_n = top_n
        self._now = now

    def build(self) -> dict:
        rates = self._rate_repository.read()
        parser = RowParser()

        status_counts: Counter[str] = Counter()
        total = _Bucket()
        monthly: defaultdict[str, _Bucket] = defaultdict(_Bucket)
        hotels: defaultdict[str, _HotelBucket] = defaultdict(_HotelBucket)

        # ler → converter tipos → contar status → filtrar CONFIRMED → agregar (linha a linha)
        for raw in self._reservation_repository.read():
            reservation = parser.parse(raw)
            status_counts[reservation.status] += 1
            if not is_billable(reservation.status):
                continue

            room_nights = calculate_room_nights(reservation.checkin, reservation.checkout, reservation.rooms)
            amount_brl = self._convert(reservation, rates)

            total.add(room_nights, amount_brl)
            monthly[reservation.checkin.strftime("%Y-%m")].add(room_nights, amount_brl)
            hotel = hotels[reservation.hotel_id]
            hotel.hotel_name = reservation.hotel_name
            hotel.add(room_nights, amount_brl)

        total_reservations = sum(status_counts.values())
        logger.info(
            "%d reservas lidas (%d faturáveis, %d hotéis, %d meses)",
            total_reservations,
            total.reservations,
            len(hotels),
            len(monthly),
        )

        return {
            "report_version": REPORT_VERSION,
            "generated_at": (self._now or datetime.now(FIXED_OFFSET)).isoformat(timespec="seconds"),
            "summary": {
                "total_reservations": total_reservations,
                "confirmed_reservations": status_counts[CONFIRMED],
                "cancelled_reservations": status_counts[CANCELLED],
                "no_show_reservations": status_counts[NO_SHOW],
                "total_room_nights": total.room_nights,
                "total_amount_brl": format_money(total.amount),
                "average_nightly_rate_brl": format_money(self._average_nightly_rate(total)),
            },
            "by_month": self._by_month(monthly),
            "top_hotels": self._top_hotels(hotels),
        }

    @staticmethod
    def _convert(reservation: Reservation, rates: dict[str, Decimal]) -> Decimal:
        try:
            return convert_to_brl(reservation.amount, reservation.currency, rates)
        except UnknownCurrencyError as err:
            raise InputFileError(f"linha {reservation.line_number} inválida: {err}") from err

    @staticmethod
    def _average_nightly_rate(total: _Bucket) -> Decimal:
        if total.room_nights <= 0:
            return Decimal("0")
        return total.amount / Decimal(total.room_nights)

    @staticmethod
    def _by_month(monthly: dict[str, _Bucket]) -> list[dict]:
        return [
            {
                "month": month,
                "reservations": bucket.reservations,
                "room_nights": bucket.room_nights,
                "total_brl": format_money(bucket.amount),
            }
            for month, bucket in sorted(monthly.items())
        ]

    def _top_hotels(self, hotels: dict[str, _HotelBucket]) -> list[dict]:
        # total_brl decrescente; empate por hotel_id ascendente.
        ranked = sorted(hotels.items(), key=lambda item: (-item[1].amount, item[0]))
        return [
            {
                "hotel_id": hotel_id,
                "hotel_name": bucket.hotel_name,
                "room_nights": bucket.room_nights,
                "total_brl": format_money(bucket.amount),
            }
            for hotel_id, bucket in ranked[: self._top_n]
        ]
