"""Roteador da versão 1 da API. Os módulos de negócio são incluídos aqui."""

from fastapi import APIRouter

from raizes.api.v1 import audit, auth, consent, orders, payments

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(orders.router)
router.include_router(payments.router)
router.include_router(consent.router)
router.include_router(audit.router)
