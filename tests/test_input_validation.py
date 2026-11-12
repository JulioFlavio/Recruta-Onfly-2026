"""Entradas inválidas devem encerrar o CLI com código 2 e mensagem clara, nunca com totais errados."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from helpers import BASE, COLUMNS, PROJECT_ROOT, SRC_DIR, run_cli

RATES = "currency,rate_to_brl\nBRL,1.000000\nUSD,5.420000\nEUR,5.880000\n"


def run_raw(tmp_path: Path, rows: list[dict[str, str]], *extra_args: str) -> subprocess.CompletedProcess:
    """Como helpers.run_cli, mas devolve o processo sem exigir sucesso."""
    input_path = tmp_path / "reservas.csv"
    rates_path = tmp_path / "rates.csv"
    with input_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({**BASE, **row} for row in rows)
    rates_path.write_text(RATES, encoding="utf-8")

    environment = {**os.environ, "PYTHONPATH": str(SRC_DIR), "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "onfly_report",
            "--input",
            str(input_path),
            "--rates",
            str(rates_path),
            "--output",
            str(tmp_path / "report.json"),
            *extra_args,
        ],
        cwd=str(PROJECT_ROOT),
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


@pytest.mark.parametrize(
    ("row", "message"),
    [
        ({"currency": "GBP"}, "moeda sem taxa"),
        ({"status": "PENDING"}, "status desconhecido"),
        ({"checkin_date": "2025-01-10", "checkout_date": "2025-01-08"}, "checkout"),
        ({"checkin_date": "2025-01-10", "checkout_date": "2025-01-10"}, "checkout"),
        ({"rooms": "0"}, "rooms"),
        ({"amount": "-10.00"}, "amount"),
        ({"amount": "abc"}, "inválida"),
        ({"checkin_date": "10/01/2025"}, "inválida"),
        ({"hotel_id": ""}, "hotel_id"),
    ],
)
def test_invalid_row_exits_with_code_2(tmp_path, row, message):
    process = run_raw(tmp_path, [{"reservation_id": "R-1"}, {"reservation_id": "R-2", **row}])

    assert process.returncode == 2, process.stderr
    assert "linha 3" in process.stderr
    assert message in process.stderr
    assert not (tmp_path / "report.json").exists()


@pytest.mark.parametrize("top", ["0", "-1", "abc"])
def test_invalid_top_exits_with_code_2(tmp_path, top):
    assert run_raw(tmp_path, [{}], "--top", top).returncode == 2


def test_missing_input_file_exits_with_code_2(tmp_path):
    process = run_raw(tmp_path, [{}], "--input", str(tmp_path / "inexistente.csv"))

    assert process.returncode == 2
    assert "não encontrado" in process.stderr


def test_lowercase_currency_and_status_are_normalized(tmp_path):
    """A tabela de câmbio já normaliza para maiúsculas; a reserva segue a mesma regra."""
    report = run_cli(tmp_path, [{"currency": "usd", "status": "confirmed", "amount": "100.00"}])

    assert report["summary"]["confirmed_reservations"] == 1
    assert report["summary"]["total_amount_brl"] == "542.00"


def test_output_is_valid_json_with_exact_schema(tmp_path):
    report = run_cli(tmp_path, [{}])

    assert list(report) == ["report_version", "generated_at", "summary", "by_month", "top_hotels"]
    assert report["report_version"] == "1.0"
    assert report["generated_at"].endswith("-03:00")
    json.dumps(report)
