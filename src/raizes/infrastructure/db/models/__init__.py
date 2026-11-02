"""Modelos ORM. Importe os módulos aqui para registrá-los no metadata (Alembic)."""

from raizes.infrastructure.db.models.outbox import OutboxEvento

__all__ = ["OutboxEvento"]
