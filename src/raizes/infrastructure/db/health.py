"""Implementação da porta DatabaseHealthCheck com SELECT 1."""

import logging

from sqlalchemy import Engine, text

logger = logging.getLogger(__name__)


class SqlDatabaseHealthCheck:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def is_available(self) -> bool:
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception:
            logger.warning("Banco de dados indisponível", exc_info=False)
            return False
        return True
