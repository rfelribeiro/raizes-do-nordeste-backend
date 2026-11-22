"""Repositório de usuários (leitura de credenciais para o login)."""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from raizes.application.identity.credentials import UserCredentials
from raizes.domain.shared.enums import Role


class SqlAlchemyUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_credentials_by_email(self, email: str) -> UserCredentials | None:
        row = self._session.execute(
            text(
                "SELECT id, perfil, id_unidade_lotacao, senha_hash, eh_ativo "
                "FROM usuarios WHERE lower(email) = lower(:email)"
            ),
            {"email": email},
        ).one_or_none()
        if row is None:
            return None
        return UserCredentials(
            user_id=UUID(str(row.id)),
            role=Role(row.perfil),
            unit_id=UUID(str(row.id_unidade_lotacao)) if row.id_unidade_lotacao else None,
            password_hash=row.senha_hash,
            is_active=bool(row.eh_ativo),
        )

    def is_active_customer(self, user_id: UUID) -> bool:
        found = self._session.execute(
            text(
                "SELECT 1 FROM usuarios "
                "WHERE id = :id AND perfil = 'CLIENTE' AND eh_ativo AND anonimizado_em IS NULL"
            ),
            {"id": user_id},
        ).first()
        return found is not None
