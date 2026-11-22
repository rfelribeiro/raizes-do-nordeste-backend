"""POST /auth/login (UC-02). Nunca registra e-mail, senha ou token em log."""

from typing import Annotated

from fastapi import APIRouter, Depends

from raizes.api.composition.identity import get_login
from raizes.api.schemas.auth import LoginRequest, TokenResponse
from raizes.application.identity.login import Login

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", summary="Autentica e devolve o token de acesso")
def login(body: LoginRequest, use_case: Annotated[Login, Depends(get_login)]) -> TokenResponse:
    issued = use_case.execute(body.email, body.senha)
    return TokenResponse(access_token=issued.access_token, expires_in=issued.expires_in)
