"""Regras de negócio do README não cobertas pelos testes fornecidos."""

from __future__ import annotations

from helpers import run_cli


def test_nights_across_year_boundary_and_multiple_rooms(tmp_path):
    report = run_cli(
        tmp_path,
        [{"checkin_date": "2024-12-31", "checkout_date": "2025-01-02", "rooms": "3"}],
    )

    assert report["summary"]["total_room_nights"] == 6
    assert report["by_month"][0]["month"] == "2024-12"


def test_by_month_uses_checkin_month_and_ascending_order(tmp_path):
    report = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "checkin_date": "2025-03-05", "checkout_date": "2025-03-06"},
            {"reservation_id": "R-2", "checkin_date": "2025-01-31", "checkout_date": "2025-02-02", "amount": "50.00"},
            {"reservation_id": "R-3", "checkin_date": "2025-01-10", "checkout_date": "2025-01-11", "amount": "25.00"},
            {"reservation_id": "R-4", "checkin_date": "2025-02-10", "checkout_date": "2025-02-11", "status": "NO_SHOW"},
        ],
    )

    assert report["by_month"] == [
        {"month": "2025-01", "reservations": 2, "room_nights": 3, "total_brl": "75.00"},
        {"month": "2025-03", "reservations": 1, "room_nights": 1, "total_brl": "100.00"},
    ]


def test_top_hotels_tie_breaks_by_hotel_id_and_respects_top(tmp_path):
    report = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "hotel_id": "H03", "hotel_name": "C", "amount": "500.00"},
            {"reservation_id": "R-2", "hotel_id": "H01", "hotel_name": "A", "amount": "500.00"},
            {"reservation_id": "R-3", "hotel_id": "H02", "hotel_name": "B", "amount": "900.00"},
            {"reservation_id": "R-4", "hotel_id": "H04", "hotel_name": "D", "amount": "10.00"},
        ],
        top=3,
    )

    assert [hotel["hotel_id"] for hotel in report["top_hotels"]] == ["H02", "H01", "H03"]


def test_top_hotels_aggregates_multiple_reservations_of_same_hotel(tmp_path):
    report = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "hotel_id": "H01", "amount": "100.00"},
            {"reservation_id": "R-2", "hotel_id": "H01", "currency": "EUR", "amount": "10.00", "rooms": "2"},
        ],
    )

    assert report["top_hotels"] == [
        {"hotel_id": "H01", "hotel_name": "Hotel Teste", "room_nights": 3, "total_brl": "158.80"},
    ]


def test_money_rounds_half_up_only_at_serialization(tmp_path):
    """0.005 + 0.005 = 0.01 exato; arredondar cada parcela antes de somar daria 0.02."""
    report = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "amount": "0.005"},
            {"reservation_id": "R-2", "amount": "0.005"},
            {"reservation_id": "R-3", "hotel_id": "H02", "amount": "0.125"},
        ],
    )

    assert report["summary"]["total_amount_brl"] == "0.14"
    assert report["by_month"][0]["total_brl"] == "0.14"
    assert {hotel["hotel_id"]: hotel["total_brl"] for hotel in report["top_hotels"]} == {
        "H01": "0.01",
        "H02": "0.13",
    }


def test_average_nightly_rate_rounds_half_up(tmp_path):
    report = run_cli(
        tmp_path,
        [{"amount": "2.01", "checkin_date": "2025-01-10", "checkout_date": "2025-01-12"}],
    )

    assert report["summary"]["average_nightly_rate_brl"] == "1.01"


def test_without_confirmed_reservations_totals_are_zero(tmp_path):
    report = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "status": "CANCELLED"},
            {"reservation_id": "R-2", "status": "NO_SHOW"},
        ],
    )

    assert report["summary"] == {
        "total_reservations": 2,
        "confirmed_reservations": 0,
        "cancelled_reservations": 1,
        "no_show_reservations": 1,
        "total_room_nights": 0,
        "total_amount_brl": "0.00",
        "average_nightly_rate_brl": "0.00",
    }
    assert report["by_month"] == []
    assert report["top_hotels"] == []
