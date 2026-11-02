#!/bin/sh
# Aplica as migrações pendentes antes de iniciar o processo principal.
set -eu
alembic upgrade head
exec "$@"
