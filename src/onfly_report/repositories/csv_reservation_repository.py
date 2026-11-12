"""Leitura da exportação de reservas em CSV."""

from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path

from ..exceptions import InputFileError
from ..models import RawRow

REQUIRED_COLUMNS = (
    "reservation_id",
    "traveler_name",
    "company_id",
    "hotel_id",
    "hotel_name",
    "city",
    "country",
    "checkin_date",
    "checkout_date",
    "rooms",
    "status",
    "currency",
    "amount",
    "payment_method",
    "booked_at",
)


class CsvReservationRepository:
    """Lê a exportação de reservas sem aplicar regra de negócio.

    As linhas são entregues uma a uma (streaming): o consumo de memória não cresce com o
    tamanho do arquivo.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def read(self) -> Iterator[RawRow]:
        try:
            # utf-8-sig aceita arquivos com BOM (comum em exportações do Excel) e sem BOM.
            with self._path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
                if missing:
                    raise InputFileError(f"colunas obrigatórias ausentes: {', '.join(missing)}")

                for values in reader:
                    yield RawRow(line_number=reader.line_num, values=values)
        except FileNotFoundError as err:
            raise InputFileError(f"arquivo de reservas não encontrado: {self._path}") from err
        except (OSError, csv.Error) as err:
            raise InputFileError(f"falha ao ler {self._path}: {err}") from err
