"""cria as tabelas do MVP

Subconjunto do DER (docs/modelagem/der.md, seção 3) exigido pelo fluxo pedido -> pagamento ->
status: unidades, usuarios, categorias, produtos, itens_cardapio, estoques, movimentacoes_estoque,
pedidos, itens_pedido, historico_status_pedido, tentativas_pagamento, consentimentos e auditoria.
Ficam fora do MVP: saldos_pontos, movimentos_pontos e chaves_idempotencia.

Os valores dos CHECKs de enum são literais (não importam o código da aplicação), para que a
migração continue reproduzível mesmo que os enums evoluam.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-22 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERFIS = "'CLIENTE', 'ATENDENTE', 'COZINHA', 'GERENTE', 'ADMIN'"
CANAIS = "'APP', 'TOTEM', 'BALCAO', 'PICKUP', 'WEB'"
STATUS_PEDIDO = "'AGUARDANDO_PAGAMENTO', 'PAGO', 'EM_PREPARO', 'PRONTO', 'ENTREGUE', 'CANCELADO'"

# Ordem de criação; o downgrade remove na ordem inversa.
TABELAS = (
    "unidades",
    "usuarios",
    "categorias",
    "produtos",
    "itens_cardapio",
    "pedidos",
    "estoques",
    "movimentacoes_estoque",
    "itens_pedido",
    "historico_status_pedido",
    "tentativas_pagamento",
    "consentimentos",
    "auditoria",
)


def _id() -> sa.Column[sa.UUID]:
    return sa.Column("id", sa.UUID(), nullable=False)


def _ts(nome: str) -> sa.Column[sa.DateTime]:
    return sa.Column(
        nome, sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )


def _fk(tabela: str, coluna: str, destino: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [coluna],
        [f"{destino}.id"],
        name=op.f(f"fk_{tabela}_{coluna}_{destino}"),
        ondelete="RESTRICT",
    )


def _ck(tabela: str, nome: str, expressao: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(expressao, name=op.f(f"ck_{tabela}_{nome}"))


def _pk(tabela: str, *colunas: str) -> sa.PrimaryKeyConstraint:
    return sa.PrimaryKeyConstraint(*colunas, name=op.f(f"pk_{tabela}"))


def _uq(tabela: str, nome: str, *colunas: str) -> sa.UniqueConstraint:
    return sa.UniqueConstraint(*colunas, name=op.f(f"uq_{tabela}_{nome}"))


def upgrade() -> None:
    # --- unidades
    op.create_table(
        "unidades",
        _id(),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("cidade", sa.String(80), nullable=False),
        sa.Column("uf", sa.CHAR(2), nullable=False),
        sa.Column("formato", sa.String(10), nullable=False),
        sa.Column("eh_ativa", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        _ts("criado_em"),
        _ts("atualizado_em"),
        _pk("unidades", "id"),
        _uq("unidades", "codigo", "codigo"),
        _ck("unidades", "uf", "uf ~ '^[A-Z]{2}$'"),
        _ck("unidades", "formato", "formato IN ('COMPLETA', 'REDUZIDA')"),
    )

    # --- usuarios
    op.create_table(
        "usuarios",
        _id(),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("senha_hash", sa.String(255), nullable=False),
        sa.Column("perfil", sa.String(10), nullable=False),
        sa.Column("id_unidade_lotacao", sa.UUID(), nullable=True),
        sa.Column("data_nascimento", sa.Date(), nullable=True),
        sa.Column("eh_ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("anonimizado_em", sa.DateTime(timezone=True), nullable=True),
        _ts("criado_em"),
        _ts("atualizado_em"),
        _pk("usuarios", "id"),
        _fk("usuarios", "id_unidade_lotacao", "unidades"),
        _ck("usuarios", "perfil", f"perfil IN ({PERFIS})"),
        _ck(
            "usuarios",
            "lotacao_por_perfil",
            "(perfil IN ('ATENDENTE', 'COZINHA', 'GERENTE') AND id_unidade_lotacao IS NOT NULL) "
            "OR (perfil IN ('CLIENTE', 'ADMIN') AND id_unidade_lotacao IS NULL)",
        ),
    )
    op.create_index("uq_usuarios_email_lower", "usuarios", [sa.text("lower(email)")], unique=True)
    op.create_index("ix_usuarios_id_unidade_lotacao", "usuarios", ["id_unidade_lotacao"])

    # --- categorias
    op.create_table(
        "categorias",
        _id(),
        sa.Column("nome", sa.String(80), nullable=False),
        _ts("criado_em"),
        _ts("atualizado_em"),
        _pk("categorias", "id"),
        _uq("categorias", "nome", "nome"),
    )

    # --- produtos
    op.create_table(
        "produtos",
        _id(),
        sa.Column("id_categoria", sa.UUID(), nullable=False),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("descricao", sa.String(500), nullable=True),
        sa.Column("valor_preco_referencia", sa.Numeric(10, 2), nullable=False),
        sa.Column("eh_sazonal", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("eh_ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        _ts("criado_em"),
        _ts("atualizado_em"),
        _pk("produtos", "id"),
        _fk("produtos", "id_categoria", "categorias"),
        _ck("produtos", "valor_preco_referencia", "valor_preco_referencia >= 0"),
    )
    op.create_index("ix_produtos_id_categoria", "produtos", ["id_categoria"])

    # --- itens_cardapio
    op.create_table(
        "itens_cardapio",
        _id(),
        sa.Column("id_unidade", sa.UUID(), nullable=False),
        sa.Column("id_produto", sa.UUID(), nullable=False),
        sa.Column("eh_disponivel", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("valor_preco_local", sa.Numeric(10, 2), nullable=True),
        sa.Column("data_inicio_sazonal", sa.Date(), nullable=True),
        sa.Column("data_fim_sazonal", sa.Date(), nullable=True),
        _ts("criado_em"),
        _ts("atualizado_em"),
        _pk("itens_cardapio", "id"),
        _fk("itens_cardapio", "id_unidade", "unidades"),
        _fk("itens_cardapio", "id_produto", "produtos"),
        _uq("itens_cardapio", "unidade_produto", "id_unidade", "id_produto"),
        _ck("itens_cardapio", "valor_preco_local", "valor_preco_local >= 0"),
        _ck(
            "itens_cardapio",
            "periodo_sazonal",
            "data_inicio_sazonal IS NULL OR data_fim_sazonal IS NULL "
            "OR data_inicio_sazonal <= data_fim_sazonal",
        ),
    )
    op.create_index("ix_itens_cardapio_id_produto", "itens_cardapio", ["id_produto"])

    # --- pedidos
    op.create_table(
        "pedidos",
        _id(),
        sa.Column("numero_pedido", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("id_unidade", sa.UUID(), nullable=False),
        sa.Column("id_cliente", sa.UUID(), nullable=True),
        sa.Column("id_usuario_criador", sa.UUID(), nullable=False),
        sa.Column("canal_pedido", sa.String(10), nullable=False),
        sa.Column("status", sa.String(21), nullable=False),
        sa.Column("valor_itens", sa.Numeric(10, 2), nullable=False),
        sa.Column("valor_desconto", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("valor_total", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "qtd_pontos_resgatados", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        _ts("criado_em"),
        _ts("atualizado_em"),
        _pk("pedidos", "id"),
        _uq("pedidos", "numero_pedido", "numero_pedido"),
        _fk("pedidos", "id_unidade", "unidades"),
        _fk("pedidos", "id_cliente", "usuarios"),
        _fk("pedidos", "id_usuario_criador", "usuarios"),
        _ck("pedidos", "canal_pedido", f"canal_pedido IN ({CANAIS})"),
        _ck("pedidos", "status", f"status IN ({STATUS_PEDIDO})"),
        _ck("pedidos", "valor_itens", "valor_itens >= 0"),
        _ck("pedidos", "valor_desconto", "valor_desconto >= 0"),
        _ck("pedidos", "valor_total", "valor_total >= 0"),
        _ck(
            "pedidos",
            "qtd_pontos_resgatados",
            "qtd_pontos_resgatados >= 0 AND qtd_pontos_resgatados % 100 = 0",
        ),
        _ck("pedidos", "valor_total_coerente", "valor_total = valor_itens - valor_desconto"),
        _ck(
            "pedidos",
            "resgate_exige_cliente",
            "qtd_pontos_resgatados = 0 OR id_cliente IS NOT NULL",
        ),
    )
    op.create_index(
        "ix_pedidos_unidade_status_criado", "pedidos", ["id_unidade", "status", "criado_em"]
    )
    op.create_index("ix_pedidos_canal_criado", "pedidos", ["canal_pedido", "criado_em"])
    op.create_index("ix_pedidos_cliente_criado", "pedidos", ["id_cliente", "criado_em"])
    op.create_index(
        "ix_pedidos_expira_em_pendentes",
        "pedidos",
        ["expira_em"],
        postgresql_where=sa.text("status = 'AGUARDANDO_PAGAMENTO'"),
    )
    op.create_index("ix_pedidos_id_usuario_criador", "pedidos", ["id_usuario_criador"])

    # --- estoques
    op.create_table(
        "estoques",
        sa.Column("id_unidade", sa.UUID(), nullable=False),
        sa.Column("id_produto", sa.UUID(), nullable=False),
        sa.Column("qtd_disponivel", sa.Integer(), nullable=False),
        sa.Column("qtd_reservada", sa.Integer(), nullable=False),
        _ts("atualizado_em"),
        _pk("estoques", "id_unidade", "id_produto"),
        _fk("estoques", "id_unidade", "unidades"),
        _fk("estoques", "id_produto", "produtos"),
        _ck("estoques", "qtd_disponivel", "qtd_disponivel >= 0"),
        _ck("estoques", "qtd_reservada", "qtd_reservada >= 0"),
    )
    op.create_index("ix_estoques_id_produto", "estoques", ["id_produto"])

    # --- movimentacoes_estoque
    op.create_table(
        "movimentacoes_estoque",
        _id(),
        sa.Column("id_unidade", sa.UUID(), nullable=False),
        sa.Column("id_produto", sa.UUID(), nullable=False),
        sa.Column("tipo", sa.String(16), nullable=False),
        sa.Column("qtd_movimentada", sa.Integer(), nullable=False),
        sa.Column("id_pedido", sa.UUID(), nullable=True),
        sa.Column("id_usuario", sa.UUID(), nullable=True),
        sa.Column("motivo", sa.String(255), nullable=True),
        _ts("ocorrido_em"),
        _pk("movimentacoes_estoque", "id"),
        _fk("movimentacoes_estoque", "id_unidade", "unidades"),
        _fk("movimentacoes_estoque", "id_produto", "produtos"),
        _fk("movimentacoes_estoque", "id_pedido", "pedidos"),
        _fk("movimentacoes_estoque", "id_usuario", "usuarios"),
        _ck(
            "movimentacoes_estoque",
            "tipo",
            "tipo IN ('ENTRADA', 'RESERVA', 'LIBERACAO', 'BAIXA', "
            "'AJUSTE_POSITIVO', 'AJUSTE_NEGATIVO')",
        ),
        _ck("movimentacoes_estoque", "qtd_movimentada", "qtd_movimentada > 0"),
    )
    op.create_index(
        "ix_movimentacoes_estoque_unidade_produto_ocorrido",
        "movimentacoes_estoque",
        ["id_unidade", "id_produto", "ocorrido_em"],
    )
    op.create_index("ix_movimentacoes_estoque_id_pedido", "movimentacoes_estoque", ["id_pedido"])
    op.create_index("ix_movimentacoes_estoque_id_usuario", "movimentacoes_estoque", ["id_usuario"])

    # --- itens_pedido
    op.create_table(
        "itens_pedido",
        _id(),
        sa.Column("id_pedido", sa.UUID(), nullable=False),
        sa.Column("id_produto", sa.UUID(), nullable=False),
        sa.Column("qtd_item", sa.Integer(), nullable=False),
        sa.Column("valor_preco_unitario", sa.Numeric(10, 2), nullable=False),
        sa.Column("valor_total_item", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "valor_desconto_item", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False
        ),
        _pk("itens_pedido", "id"),
        _fk("itens_pedido", "id_pedido", "pedidos"),
        _fk("itens_pedido", "id_produto", "produtos"),
        _uq("itens_pedido", "pedido_produto", "id_pedido", "id_produto"),
        _ck("itens_pedido", "qtd_item", "qtd_item > 0"),
        _ck("itens_pedido", "valor_preco_unitario", "valor_preco_unitario >= 0"),
        _ck(
            "itens_pedido", "valor_total_item", "valor_total_item = qtd_item * valor_preco_unitario"
        ),
        _ck(
            "itens_pedido",
            "valor_desconto_item",
            "valor_desconto_item >= 0 AND valor_desconto_item <= valor_total_item",
        ),
    )
    op.create_index("ix_itens_pedido_id_produto", "itens_pedido", ["id_produto"])

    # --- historico_status_pedido
    op.create_table(
        "historico_status_pedido",
        _id(),
        sa.Column("id_pedido", sa.UUID(), nullable=False),
        sa.Column("status_anterior", sa.String(21), nullable=True),
        sa.Column("status_novo", sa.String(21), nullable=False),
        sa.Column("id_usuario", sa.UUID(), nullable=True),
        sa.Column("motivo", sa.String(255), nullable=True),
        _ts("ocorrido_em"),
        _pk("historico_status_pedido", "id"),
        _fk("historico_status_pedido", "id_pedido", "pedidos"),
        _fk("historico_status_pedido", "id_usuario", "usuarios"),
        _ck(
            "historico_status_pedido",
            "status_anterior",
            f"status_anterior IS NULL OR status_anterior IN ({STATUS_PEDIDO})",
        ),
        _ck("historico_status_pedido", "status_novo", f"status_novo IN ({STATUS_PEDIDO})"),
        _ck(
            "historico_status_pedido",
            "status_diferente",
            "status_anterior IS DISTINCT FROM status_novo",
        ),
    )
    op.create_index(
        "ix_historico_status_pedido_pedido_ocorrido",
        "historico_status_pedido",
        ["id_pedido", "ocorrido_em"],
    )
    op.create_index(
        "ix_historico_status_pedido_id_usuario", "historico_status_pedido", ["id_usuario"]
    )

    # --- tentativas_pagamento
    op.create_table(
        "tentativas_pagamento",
        _id(),
        sa.Column("id_pedido", sa.UUID(), nullable=False),
        sa.Column("numero_tentativa", sa.Integer(), nullable=False),
        sa.Column(
            "qtd_chamadas_gateway", sa.Integer(), server_default=sa.text("1"), nullable=False
        ),
        sa.Column("forma_pagamento", sa.String(7), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("valor", sa.Numeric(10, 2), nullable=False),
        sa.Column("motivo_recusa", sa.String(255), nullable=True),
        sa.Column("id_transacao_gateway", sa.String(80), nullable=True),
        sa.Column("payload_resposta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        _ts("solicitado_em"),
        sa.Column("respondido_em", sa.DateTime(timezone=True), nullable=True),
        _ts("atualizado_em"),
        _pk("tentativas_pagamento", "id"),
        _fk("tentativas_pagamento", "id_pedido", "pedidos"),
        _uq("tentativas_pagamento", "pedido_numero", "id_pedido", "numero_tentativa"),
        _ck("tentativas_pagamento", "numero_tentativa", "numero_tentativa >= 1"),
        _ck(
            "tentativas_pagamento",
            "qtd_chamadas_gateway",
            "qtd_chamadas_gateway BETWEEN 1 AND 3",
        ),
        _ck(
            "tentativas_pagamento",
            "forma_pagamento",
            "forma_pagamento IN ('PIX', 'CREDITO', 'DEBITO')",
        ),
        _ck(
            "tentativas_pagamento",
            "status",
            "status IN ('PENDENTE', 'APROVADO', 'RECUSADO', 'FALHA', 'ESTORNADO')",
        ),
        _ck("tentativas_pagamento", "valor", "valor > 0"),
        _ck(
            "tentativas_pagamento",
            "respondido_apos_solicitado",
            "respondido_em IS NULL OR respondido_em >= solicitado_em",
        ),
    )
    op.create_index(
        "uq_tentativas_pagamento_pedido_efetivada",
        "tentativas_pagamento",
        ["id_pedido"],
        unique=True,
        postgresql_where=sa.text("status IN ('APROVADO', 'ESTORNADO')"),
    )

    # --- consentimentos
    op.create_table(
        "consentimentos",
        _id(),
        sa.Column("id_usuario", sa.UUID(), nullable=False),
        sa.Column("finalidade", sa.String(15), nullable=False),
        sa.Column("acao", sa.String(9), nullable=False),
        sa.Column("base_legal", sa.String(60), nullable=False),
        sa.Column("versao_termo", sa.String(20), nullable=False),
        _ts("registrado_em"),
        _pk("consentimentos", "id"),
        _fk("consentimentos", "id_usuario", "usuarios"),
        _ck(
            "consentimentos",
            "finalidade",
            "finalidade IN ('FIDELIDADE', 'MARKETING', 'DATA_NASCIMENTO')",
        ),
        _ck("consentimentos", "acao", "acao IN ('CONCEDIDO', 'REVOGADO')"),
    )
    op.create_index(
        "ix_consentimentos_vigente",
        "consentimentos",
        ["id_usuario", "finalidade", sa.text("registrado_em DESC")],
        postgresql_include=["acao"],
    )

    # --- auditoria
    op.create_table(
        "auditoria",
        _id(),
        _ts("ocorrido_em"),
        sa.Column("id_usuario", sa.UUID(), nullable=True),
        sa.Column("perfil", sa.String(10), nullable=True),
        sa.Column("acao", sa.String(40), nullable=False),
        sa.Column("tipo_recurso", sa.String(30), nullable=False),
        sa.Column("id_recurso", sa.String(64), nullable=False),
        sa.Column("id_unidade", sa.UUID(), nullable=True),
        sa.Column("canal_pedido", sa.String(10), nullable=True),
        sa.Column("id_requisicao", sa.String(64), nullable=False),
        sa.Column(
            "detalhes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        _pk("auditoria", "id"),
        _fk("auditoria", "id_usuario", "usuarios"),
        _fk("auditoria", "id_unidade", "unidades"),
        _ck("auditoria", "perfil", f"perfil IS NULL OR perfil IN ({PERFIS})"),
        _ck("auditoria", "canal_pedido", f"canal_pedido IS NULL OR canal_pedido IN ({CANAIS})"),
        _ck("auditoria", "autor_com_perfil", "(id_usuario IS NULL) = (perfil IS NULL)"),
    )
    op.create_index("ix_auditoria_ocorrido_em", "auditoria", ["ocorrido_em"])
    op.create_index("ix_auditoria_unidade_ocorrido", "auditoria", ["id_unidade", "ocorrido_em"])
    op.create_index("ix_auditoria_recurso", "auditoria", ["tipo_recurso", "id_recurso"])
    op.create_index("ix_auditoria_id_requisicao", "auditoria", ["id_requisicao"])
    op.create_index("ix_auditoria_id_usuario", "auditoria", ["id_usuario"])


def downgrade() -> None:
    # Ordem inversa da criação; os índices caem junto com as tabelas.
    for tabela in reversed(TABELAS):
        op.drop_table(tabela)
