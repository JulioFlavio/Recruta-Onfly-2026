"""Conversão de valores para BRL."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from ..exceptions import UnknownCurrencyError


def convert_to_brl(amount: Decimal, currency: str, rates: Mapping[str, Decimal]) -> Decimal:
    """Converte um valor na moeda informada para BRL usando a taxa da tabela."""
    try:
        rate = rates[currency]
    except KeyError:
        raise UnknownCurrencyError(currency) from None
    return amount * rate
