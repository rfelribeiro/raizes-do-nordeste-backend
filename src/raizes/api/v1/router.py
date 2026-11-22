"""Roteador da versão 1 da API. Os módulos de negócio são incluídos aqui."""

from fastapi import APIRouter

from raizes.api.v1 import auth

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
