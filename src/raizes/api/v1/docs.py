"""Ajudante para documentar no OpenAPI as respostas de erro de cada rota (RNF-12)."""

from typing import Any

from raizes.api.schemas.erro import ErroPadrao

ErroDoc = tuple[int, str, str, str]


def erros(*items: ErroDoc) -> dict[int | str, Any]:
    """`responses` do FastAPI: modelo de erro padrão e um exemplo por status."""
    return {
        status: {
            "model": ErroPadrao,
            "description": descricao,
            "content": {
                "application/json": {
                    "example": {
                        "error": codigo,
                        "message": mensagem,
                        "details": [],
                        "timestamp": "2026-02-05T12:00:00Z",
                        "path": "/api/v1/pedidos",
                        "requestId": "3f2c9a1e7b6d4c58",
                    }
                }
            },
        }
        for status, descricao, codigo, mensagem in items
    }


E401: ErroDoc = (
    401,
    "Token ausente, inválido ou expirado",
    "NAO_AUTENTICADO",
    "Autenticação necessária.",
)
E403: ErroDoc = (
    403,
    "Sem permissão (perfil ou unidade)",
    "SEM_PERMISSAO",
    "Você não tem permissão para esta operação.",
)
E404: ErroDoc = (
    404,
    "Recurso inexistente (ou de outro cliente)",
    "NAO_ENCONTRADO",
    "Pedido não encontrado.",
)
E409_ESTOQUE: ErroDoc = (
    409,
    "Estoque insuficiente",
    "ESTOQUE_INSUFICIENTE",
    "Não há quantidade suficiente para um ou mais itens.",
)
E409_TRANSICAO: ErroDoc = (
    409,
    "Transição de status inválida",
    "TRANSICAO_INVALIDA",
    "Transição de PAGO para ENTREGUE não é permitida.",
)
E409_PAGAMENTO: ErroDoc = (
    409,
    "Pedido fora de AGUARDANDO_PAGAMENTO ou com pagamento em andamento",
    "PEDIDO_FORA_DE_AGUARDANDO_PAGAMENTO",
    "O pedido não está aguardando pagamento.",
)
E409_CONSENTIMENTO: ErroDoc = (
    409,
    "Concessão repetida ou revogação sem consentimento vigente",
    "CONSENTIMENTO_JA_CONCEDIDO",
    "A finalidade já está concedida.",
)
E422: ErroDoc = (
    422,
    "Validação falhou",
    "VALIDACAO_FALHOU",
    "Um ou mais campos da requisição são inválidos.",
)
E504: ErroDoc = (
    504,
    "Gateway de pagamento sem resposta após as novas tentativas",
    "TEMPO_ESGOTADO",
    "O gateway de pagamento não respondeu a tempo.",
)
