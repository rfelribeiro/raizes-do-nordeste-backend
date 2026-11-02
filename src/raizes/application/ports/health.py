"""Porta para verificação de saúde do banco de dados."""

from typing import Protocol


class DatabaseHealthCheck(Protocol):
    """Contrato que a infraestrutura implementa para checar o banco."""

    def is_available(self) -> bool:
        """Retorna True se o banco responde; nunca propaga exceções de conexão."""
        ...
