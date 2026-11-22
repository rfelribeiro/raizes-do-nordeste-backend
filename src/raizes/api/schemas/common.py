"""Tipos e base compartilhados pelos schemas de negócio."""

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer

# Valor monetário na resposta: string decimal com 2 casas (ex.: "12.50").
Money = Annotated[
    Decimal,
    PlainSerializer(lambda value: f"{value:.2f}", return_type=str),
]


class ApiModel(BaseModel):
    """Base: campos com `alias` em camelCase/português exatamente como no contrato."""

    model_config = ConfigDict(populate_by_name=True)
