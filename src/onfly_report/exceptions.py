"""Exceções de domínio do consolidador de reservas."""


class DomainError(Exception):
    """Erro base do domínio."""


class InputFileError(DomainError):
    """Arquivo de entrada ausente, ilegível ou fora do formato esperado."""


class UnknownCurrencyError(InputFileError):
    """Moeda da reserva sem taxa de câmbio na tabela."""

    def __init__(self, currency: str) -> None:
        super().__init__(f"moeda sem taxa de câmbio: {currency}")
        self.currency = currency
