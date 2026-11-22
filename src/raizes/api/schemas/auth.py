"""Schemas do módulo de autenticação."""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class LoginRequest(BaseModel):
    model_config = _CONFIG

    email: str = Field(min_length=3, max_length=254, examples=["cliente@exemplo.com"])
    senha: str = Field(min_length=1, max_length=128, description="Senha em texto (só no login)")


class TokenResponse(BaseModel):
    model_config = _CONFIG

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Validade do token em segundos", examples=[3600])
