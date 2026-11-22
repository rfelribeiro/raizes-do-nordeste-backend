"""Dependências do FastAPI. Aqui (e em main.py) ocorre a composição com a infraestrutura."""

from raizes.application.ports.health import DatabaseHealthCheck
from raizes.infrastructure.db.health import SqlDatabaseHealthCheck
from raizes.infrastructure.db.session import get_engine


def get_database_health_check() -> DatabaseHealthCheck:
    return SqlDatabaseHealthCheck(get_engine())
