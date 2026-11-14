"""Evento de domínio: fato de negócio já ocorrido, base da captura OLTP -> analítico (outbox).

REGRA DE PRIVACIDADE (LGPD): eventos NÃO carregam dados pessoais em claro. Use identificadores
internos (ex.: `cliente_id`), nunca nome, CPF, e-mail, telefone, endereço ou data de nascimento.
Quando a análise precisar de um atributo derivado (ex.: faixa etária), o evento carrega o
atributo já derivado, não o dado bruto. O payload é gravado na outbox e copiado para o lake
(bronze, imutável), então o que entra no evento é, na prática, permanente.

Somente biblioteca padrão: o domínio não depende de frameworks.
"""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, ClassVar
from uuid import UUID, uuid4

_CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")


def _snake_case(name: str) -> str:
    return _CAMEL_BOUNDARY.sub("_", name).lower()


def _now_utc() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Base imutável dos eventos de domínio.

    `event_type` é um nome estável usado pelo analítico (coluna `tipo_evento`). O padrão de
    nomenclatura é snake_case em português, `<entidade>_<particípio>` (ex.: `pedido_criado`,
    `pagamento_aprovado`; ADR 0010). Como as classes são em inglês (`OrderCreated`), cada evento
    de negócio deve DECLARAR `event_type` explicitamente como atributo de classe; o derivado do
    nome da classe (`OrderCreated` -> `order_created`) é só um valor de reserva. Renomear a classe
    NÃO deve mudar o nome do evento já publicado. Mudanças incompatíveis no payload exigem
    aumentar `schema_version`.
    """

    event_type: ClassVar[str] = ""

    aggregate_type: str
    aggregate_id: str
    schema_version: int = 1
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=_now_utc)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not cls.__dict__.get("event_type"):
            cls.event_type = _snake_case(cls.__name__)

    def __post_init__(self) -> None:
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("occurred_at deve ser um datetime com fuso horário (UTC)")
        if self.occurred_at.utcoffset() != UTC.utcoffset(None):
            object.__setattr__(self, "occurred_at", self.occurred_at.astimezone(UTC))
        if self.schema_version < 1:
            raise ValueError("schema_version deve ser >= 1")

    def payload(self) -> dict[str, Any]:
        """Conteúdo específico do evento, serializável em JSON e sem PII em claro."""
        return {}
