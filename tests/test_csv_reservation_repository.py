"""Testes do repositório que lê a exportação de reservas em CSV."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from helpers import BASE, COLUMNS

from onfly_report.exceptions import InputFileError
from onfly_report.repositories.csv_reservation_repository import CsvReservationRepository


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str] = COLUMNS) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows({**BASE, **row} for row in rows)
    return path


def test_reads_every_row_without_limit(tmp_path):
    """Nenhuma linha pode ser descartada, mesmo em arquivos grandes."""
    rows = [{"reservation_id": f"R-{i}"} for i in range(1, 301)]
    path = write_csv(tmp_path / "reservas.csv", rows)

    result = list(CsvReservationRepository(path).read())

    assert len(result) == 300
    assert result[-1].values["reservation_id"] == "R-300"


def test_keeps_raw_values_and_physical_line_numbers(tmp_path):
    """Valores chegam crus (sem conversão) e line_number aponta a linha física do arquivo."""
    path = write_csv(
        tmp_path / "reservas.csv",
        [
            {"reservation_id": "R-1", "hotel_name": "Hotel Madrid, Gran Vía", "amount": "100.00"},
            {"reservation_id": "R-2", "status": "CANCELLED"},
        ],
    )

    result = list(CsvReservationRepository(path).read())

    assert [row.line_number for row in result] == [2, 3]
    assert result[0].values["hotel_name"] == "Hotel Madrid, Gran Vía"
    assert result[0].values["amount"] == "100.00"
    assert result[1].values["status"] == "CANCELLED"


def test_empty_file_with_header_returns_no_rows(tmp_path):
    path = write_csv(tmp_path / "reservas.csv", [])

    assert list(CsvReservationRepository(path).read()) == []


def test_missing_required_column_raises_input_error(tmp_path):
    columns = [column for column in COLUMNS if column != "amount"]
    path = write_csv(tmp_path / "reservas.csv", [{}], columns=columns)

    with pytest.raises(InputFileError, match="amount"):
        list(CsvReservationRepository(path).read())


def test_accepts_utf8_bom(tmp_path):
    """Exportações do Excel costumam gravar BOM; o cabeçalho deve ser reconhecido mesmo assim."""
    path = write_csv(tmp_path / "reservas.csv", [{}])
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())

    result = list(CsvReservationRepository(path).read())

    assert result[0].values["reservation_id"] == "R-1"


def test_missing_file_raises_input_error(tmp_path):
    with pytest.raises(InputFileError, match="não encontrado"):
        list(CsvReservationRepository(tmp_path / "inexistente.csv").read())
