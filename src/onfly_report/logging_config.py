"""Configuração de logging do CLI (sempre em stderr)."""

from __future__ import annotations

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Configura o logger raiz para stderr, mantendo o stdout para o resumo."""
    # No Windows o stderr usa a code page local (ex.: cp1252) e corrompe acentos em terminais
    # e ferramentas que esperam UTF-8. Força UTF-8 de forma independente da plataforma.
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(
        level=level,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
