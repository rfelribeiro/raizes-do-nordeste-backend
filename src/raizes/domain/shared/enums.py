"""Enumerações do domínio (contrato compartilhado entre os módulos).

Os VALORES são exatamente os dos `CHECK ... IN` do DER (docs/modelagem/der.md) e do contrato da
API: MAIÚSCULAS, em português, sem acento. Os NOMES das classes seguem a convenção do código
(inglês, ADR 0010 item 3; mapeamento em docs/modelagem/classes.md §5).

Este arquivo é a fonte única desses domínios no código: ORM (CHECKs da migração), schemas da API
e regras de domínio importam daqui. Somente biblioteca padrão.
"""

from enum import StrEnum


class Role(StrEnum):
    """Perfil de acesso (`usuarios.perfil`). Um perfil por usuário (D-049)."""

    CLIENTE = "CLIENTE"
    ATENDENTE = "ATENDENTE"
    COZINHA = "COZINHA"
    GERENTE = "GERENTE"
    ADMIN = "ADMIN"


class UnitFormat(StrEnum):
    """Formato de operação da unidade (`unidades.formato`)."""

    COMPLETA = "COMPLETA"
    REDUZIDA = "REDUZIDA"


class OrderChannel(StrEnum):
    """Canal de origem do pedido (`canalPedido`; `pedidos.canal_pedido`). Imutável (RN-11)."""

    APP = "APP"
    TOTEM = "TOTEM"
    BALCAO = "BALCAO"
    PICKUP = "PICKUP"
    WEB = "WEB"


class OrderStatus(StrEnum):
    """Status do pedido (`pedidos.status`). Transições em docs/requisitos/README.md §5."""

    AGUARDANDO_PAGAMENTO = "AGUARDANDO_PAGAMENTO"
    PAGO = "PAGO"
    EM_PREPARO = "EM_PREPARO"
    PRONTO = "PRONTO"
    ENTREGUE = "ENTREGUE"
    CANCELADO = "CANCELADO"


class StockMovementType(StrEnum):
    """Tipo do movimento de estoque (`movimentacoes_estoque.tipo`); quantidade sempre > 0."""

    ENTRADA = "ENTRADA"
    RESERVA = "RESERVA"
    LIBERACAO = "LIBERACAO"
    BAIXA = "BAIXA"
    AJUSTE_POSITIVO = "AJUSTE_POSITIVO"
    AJUSTE_NEGATIVO = "AJUSTE_NEGATIVO"


class PointsMovementType(StrEnum):
    """Tipo do movimento de pontos (`movimentos_pontos.tipo`); o sinal da quantidade vem do tipo."""

    ACUMULO = "ACUMULO"
    RESGATE = "RESGATE"
    ESTORNO_ACUMULO = "ESTORNO_ACUMULO"
    ESTORNO_RESGATE = "ESTORNO_RESGATE"
    REVOGACAO = "REVOGACAO"
    EXPIRACAO = "EXPIRACAO"


class PaymentMethod(StrEnum):
    """Forma de pagamento (`formaPagamento`; `tentativas_pagamento.forma_pagamento`)."""

    PIX = "PIX"
    CREDITO = "CREDITO"
    DEBITO = "DEBITO"


class PaymentAttemptStatus(StrEnum):
    """Resultado da tentativa de pagamento; `FALHA` = timeout esgotado (D-051)."""

    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"
    FALHA = "FALHA"
    ESTORNADO = "ESTORNADO"


class ConsentPurpose(StrEnum):
    """Finalidade do consentimento (`consentimentos.finalidade`); conjunto fechado (D-054)."""

    FIDELIDADE = "FIDELIDADE"
    MARKETING = "MARKETING"
    DATA_NASCIMENTO = "DATA_NASCIMENTO"


class ConsentAction(StrEnum):
    """Concessão ou revogação (`consentimentos.acao`); o vigente é o último registro."""

    CONCEDIDO = "CONCEDIDO"
    REVOGADO = "REVOGADO"
