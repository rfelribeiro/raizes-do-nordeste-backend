"""Formato padrão de erro da API (roteiro da trilha; ADR 0011)."""

from pydantic import BaseModel, ConfigDict, Field


class DetalheErro(BaseModel):
    """Um problema específico, normalmente associado a um campo da requisição."""

    field: str = Field(
        description="Caminho do campo, ex.: itens[0].quantidade", examples=["itens[0].quantidade"]
    )
    issue: str = Field(description="Descrição do problema", examples=["Disponível: 1"])


class ErroPadrao(BaseModel):
    """Corpo de TODA resposta de erro (4xx e 5xx), com `application/json`."""

    model_config = ConfigDict(populate_by_name=True)

    error: str = Field(
        description="Código do erro em MAIÚSCULAS, estável para o cliente tratar",
        examples=["ESTOQUE_INSUFICIENTE"],
    )
    message: str = Field(
        description="Mensagem legível em português",
        examples=["Não há quantidade suficiente para um ou mais itens."],
    )
    details: list[DetalheErro] = Field(default_factory=list, description="Problemas por campo")
    timestamp: str = Field(
        description="Instante do erro em UTC (ISO-8601)", examples=["2026-02-05T12:00:00Z"]
    )
    path: str = Field(description="Rota requisitada", examples=["/pedidos"])
    request_id: str | None = Field(
        default=None,
        alias="requestId",
        description="Valor de X-Request-ID, para correlacionar com os logs",
    )


# Respostas de erro comuns, registradas no OpenAPI para o Swagger documentar o padrão.
RESPOSTAS_DE_ERRO: dict[int | str, dict[str, object]] = {
    400: {"model": ErroPadrao, "description": "Requisição inválida"},
    401: {"model": ErroPadrao, "description": "Não autenticado"},
    403: {"model": ErroPadrao, "description": "Sem permissão"},
    404: {"model": ErroPadrao, "description": "Não encontrado"},
    409: {"model": ErroPadrao, "description": "Conflito ou regra de negócio violada"},
    422: {"model": ErroPadrao, "description": "Validação falhou"},
    500: {"model": ErroPadrao, "description": "Erro interno"},
}
