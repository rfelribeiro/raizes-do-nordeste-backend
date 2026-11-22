"""Emissão e validação de JWT (HS256, RNF-02)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from raizes.application.errors import AuthenticationError
from raizes.application.ports.security import IssuedToken
from raizes.application.principal import Principal
from raizes.domain.shared.enums import Role

ISSUER = "raizes-api"
ALGORITHM = "HS256"


class JwtTokenService:
    def __init__(self, secret: str, expires_minutes: int = 60) -> None:
        self._secret = secret
        self._expires_minutes = expires_minutes

    def issue(self, principal: Principal) -> IssuedToken:
        now = datetime.now(UTC)
        expires = timedelta(minutes=self._expires_minutes)
        claims = {
            "sub": str(principal.user_id),
            "perfil": principal.role.value,
            "unidade": str(principal.unit_id) if principal.unit_id else None,
            "iat": now,
            "exp": now + expires,
            "iss": ISSUER,
        }
        token = jwt.encode(claims, self._secret, algorithm=ALGORITHM)
        return IssuedToken(access_token=token, expires_in=int(expires.total_seconds()))

    def decode(self, token: str) -> Principal:
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=[ALGORITHM],
                issuer=ISSUER,
                options={"require": ["sub", "perfil", "iat", "exp", "iss"]},
            )
            unit = claims.get("unidade")
            return Principal(
                user_id=UUID(claims["sub"]),
                role=Role(claims["perfil"]),
                unit_id=UUID(unit) if unit else None,
            )
        except (jwt.PyJWTError, ValueError, TypeError) as exc:
            raise AuthenticationError("Token inválido ou expirado.") from exc
