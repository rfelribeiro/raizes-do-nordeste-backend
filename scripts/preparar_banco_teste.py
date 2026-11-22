"""Cria o banco de testes `<POSTGRES_DB>_teste` se ele ainda não existir.

Os testes de integração usam esse banco (e nunca o de desenvolvimento), porque a limpeza entre
testes apaga todas as tabelas. Uso: `make test-integration` (que também aplica as migrações).
Conecta com as variáveis de ambiente da aplicação; não imprime credenciais.
"""

from sqlalchemy import create_engine, text

from raizes.infrastructure.config import get_settings


def main() -> None:
    settings = get_settings()
    test_db = f"{settings.postgres_db}_teste"
    engine = create_engine(settings.database_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        exists = connection.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": test_db}
        )
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{test_db}"'))
            print(f"Banco de testes criado: {test_db}")
        else:
            print(f"Banco de testes já existe: {test_db}")
    engine.dispose()


if __name__ == "__main__":
    main()
