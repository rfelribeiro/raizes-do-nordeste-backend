"""Painel de vendas da Raízes do Nordeste (MOCKUP com dados fictícios).

Lê SOMENTE a camada gold do DW (DuckDB, modo somente leitura): fatos `fct_pedido` e
`fct_tentativa_pagamento` e dimensões `dim_*`. Nunca lê o bronze nem a silver.

Os dados vêm de um histórico sintético (`make dw-simulado`); o painel serve para apresentar o que o
DW consolida para decisão: vendas por unidade e região, relatórios financeiros e picos de demanda.

Definições dos indicadores (todas sobre a gold):
  - Pedidos: pedidos criados no período.
  - Faturamento líquido: soma de `valor_liquido` dos pedidos que chegaram a ser pagos e não foram
    cancelados (status atual PAGO, EM_PREPARO, PRONTO ou ENTREGUE).
  - Ticket médio: faturamento líquido / pedidos faturados.
  - Taxa de recusa: tentativas de pagamento recusadas / tentativas com resultado.
  - Cliente identificado: pedidos com cliente (`sk_cliente` diferente de -1) / pedidos.
"""

import os
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB_PATH = os.environ.get("DW_DUCKDB_PATH", "data/warehouse/raizes_simulado.duckdb")
UNIDADES_CSV = Path(__file__).with_name("unidades_mockup.csv")

# Paleta sóbria e poucos tons.
VERDE = "#2F5D50"
OCRE = "#C8873A"
CINZA = "#8A8F98"
VERMELHO = "#B5473A"
CLARO = "#DDE5E1"

ROTULO_STATUS = {
    "AGUARDANDO_PAGAMENTO": "Aguardando pagamento",
    "PAGO": "Pago",
    "EM_PREPARO": "Em preparo",
    "PRONTO": "Pronto",
    "ENTREGUE": "Entregue",
    "CANCELADO": "Cancelado",
}
ROTULO_CANAL = {
    "APP": "App",
    "WEB": "Web",
    "PICKUP": "Retirada",
    "TOTEM": "Totem",
    "BALCAO": "Balcão",
}
ROTULO_FORMA = {"PIX": "PIX", "CREDITO": "Crédito", "DEBITO": "Débito"}
STATUS_FATURADOS = ("PAGO", "EM_PREPARO", "PRONTO", "ENTREGUE")

st.set_page_config(
    page_title="Raízes do Nordeste — Painel de vendas", page_icon="🌿", layout="wide"
)


st.markdown(
    "<style>[data-testid='stMetricValue']{font-size:1.65rem}"
    "[data-testid='stMetricLabel'] p{font-size:.85rem}</style>",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------------------------
# Formatação brasileira
# --------------------------------------------------------------------------------------------


def brl(valor: float) -> str:
    """R$ 1.234,56"""
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def inteiro(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def percentual(valor: float) -> str:
    return f"{valor * 100:.1f}".replace(".", ",") + "%"


def estilizar(fig: go.Figure, altura: int = 340) -> go.Figure:
    """Estilo comum: fundo limpo, separadores brasileiros e margens enxutas."""
    fig.update_layout(
        height=altura,
        margin={"l": 8, "r": 8, "t": 36, "b": 8},
        separators=",.",
        font={"family": "sans-serif", "size": 13},
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.0, "x": 0, "title": None},
        title={"font": {"size": 15}},
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor=CLARO)
    return fig


# --------------------------------------------------------------------------------------------
# Acesso à gold (somente leitura, com cache)
# --------------------------------------------------------------------------------------------


def _mtime() -> float:
    try:
        return os.path.getmtime(DB_PATH)
    except OSError:
        return 0.0


@st.cache_data(ttl=600, show_spinner=False)
def consultar(sql: str, parametros: tuple, mtime: float) -> pd.DataFrame:
    """Executa SQL sobre a gold. `mtime` invalida o cache quando o arquivo é regerado."""
    conexao = duckdb.connect(DB_PATH, read_only=True)
    try:
        return conexao.execute(sql, list(parametros)).df()
    finally:
        conexao.close()


def q(sql: str, parametros: tuple = ()) -> pd.DataFrame:
    return consultar(sql, parametros, _mtime())


@st.cache_data(show_spinner=False)
def carregar_unidades() -> pd.DataFrame:
    """Mapeamento id -> nome FICTÍCIO das unidades (paliativo; ver nota de rodapé)."""
    return pd.read_csv(UNIDADES_CSV, dtype=str)


def filtro_sql(alias_data: str, datas, unidades: list[int], canais: list[int]) -> tuple[str, tuple]:
    """Cláusula WHERE dos fatos (`f.sk_data`, `f.sk_unidade`, `f.sk_canal`) e seus parâmetros."""
    ini, fim = datas
    marcas_u = ",".join("?" for _ in unidades)
    marcas_c = ",".join("?" for _ in canais)
    clausula = (
        f"{alias_data}.sk_data between ? and ? "
        f"and f.sk_unidade in ({marcas_u}) and f.sk_canal in ({marcas_c})"
    )
    parametros = (int(ini.strftime("%Y%m%d")), int(fim.strftime("%Y%m%d")), *unidades, *canais)
    return clausula, parametros


# --------------------------------------------------------------------------------------------
# Cabeçalho e filtros
# --------------------------------------------------------------------------------------------

st.title("Raízes do Nordeste — Painel de vendas (mockup)")
st.warning("Dados fictícios gerados por simulação; mockup para apresentação.", icon="⚠️")

if not Path(DB_PATH).exists():
    st.error("Arquivo do DW simulado não encontrado. Rode `make dw-simulado` e recarregue.")
    st.stop()

periodo = q(
    "select min(t.data) as ini, max(t.data) as fim "
    "from gold.fct_pedido f join gold.dim_tempo t using (sk_data)"
)
if periodo.empty or pd.isna(periodo.loc[0, "ini"]):
    st.error("A gold não tem pedidos. Rode `make dw-simulado`.")
    st.stop()
data_min, data_max = periodo.loc[0, "ini"], periodo.loc[0, "fim"]

dim_unidade = q("select sk_unidade, id_unidade from gold.dim_unidade where sk_unidade <> -1")
nomes = carregar_unidades().set_index("id_unidade")
dim_unidade["rotulo"] = (
    dim_unidade["id_unidade"].map(nomes["nome"]).fillna(dim_unidade["id_unidade"].str[:8] + "…")
)
dim_unidade["cidade"] = dim_unidade["id_unidade"].map(nomes["cidade"]).fillna("—")
dim_unidade["uf"] = dim_unidade["id_unidade"].map(nomes["uf"]).fillna("—")
dim_canal = q("select sk_canal, nome_canal, tipo_canal from gold.dim_canal where sk_canal <> -1")
dim_canal["rotulo"] = dim_canal["nome_canal"].map(ROTULO_CANAL)

with st.sidebar:
    st.header("Filtros")
    selecionado = st.date_input(
        "Período", value=(data_min, data_max), min_value=data_min, max_value=data_max,
        format="DD/MM/YYYY",
    )  # fmt: skip
    unidades_sel = st.multiselect(
        "Unidade", dim_unidade["rotulo"].tolist(), default=dim_unidade["rotulo"].tolist()
    )
    canais_sel = st.multiselect(
        "Canal", dim_canal["rotulo"].tolist(), default=dim_canal["rotulo"].tolist()
    )
    st.caption("Dados fictícios (simulação).")

if not isinstance(selecionado, tuple) or len(selecionado) != 2:
    st.info("Selecione a data inicial e a final do período.")
    st.stop()
sk_unidades = dim_unidade.loc[dim_unidade["rotulo"].isin(unidades_sel), "sk_unidade"].tolist()
sk_canais = dim_canal.loc[dim_canal["rotulo"].isin(canais_sel), "sk_canal"].tolist()
if not sk_unidades or not sk_canais:
    st.info("Selecione ao menos uma unidade e um canal.")
    st.stop()

where, params = filtro_sql("f", selecionado, sk_unidades, sk_canais)
faturado = "s.nome_status_pedido in ('PAGO','EM_PREPARO','PRONTO','ENTREGUE')"

# --------------------------------------------------------------------------------------------
# 1. KPIs
# --------------------------------------------------------------------------------------------

kpi = q(
    f"""
    select count(*) as pedidos,
           sum(case when {faturado} then f.valor_liquido else 0 end) as faturamento,
           sum(case when {faturado} then 1 else 0 end) as faturados,
           avg(case when f.sk_cliente <> -1 then 1.0 else 0.0 end) as identificados
    from gold.fct_pedido f join gold.dim_status_pedido s using (sk_status_pedido)
    where {where}
    """,
    params,
).iloc[0]
pagto = q(
    f"""
    select count(*) as tentativas,
           sum(case when resultado = 'RECUSADO' then 1 else 0 end) as recusas
    from gold.fct_tentativa_pagamento f where {where}
    """,
    params,
).iloc[0]

if kpi["pedidos"] == 0:
    st.info("Nenhum pedido para os filtros escolhidos.")
    st.stop()

ticket = kpi["faturamento"] / kpi["faturados"] if kpi["faturados"] else 0
taxa_recusa = pagto["recusas"] / pagto["tentativas"] if pagto["tentativas"] else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Pedidos", inteiro(kpi["pedidos"]))
c2.metric("Faturamento líquido", brl(float(kpi["faturamento"])))
c3.metric("Ticket médio", brl(float(ticket)))
c4.metric("Taxa de recusa de pagamento", percentual(taxa_recusa))
c5.metric("Pedidos com cliente identificado", percentual(float(kpi["identificados"])))
st.caption(
    "Faturamento líquido: pedidos pagos e não cancelados. Taxa de recusa: tentativas recusadas "
    "sobre tentativas com resultado."
)

# --------------------------------------------------------------------------------------------
# 2. Faturamento no tempo (com o período junino destacado)
# --------------------------------------------------------------------------------------------

st.subheader("Faturamento no tempo")
agregacao = st.radio("Granularidade", ["Diária", "Semanal"], horizontal=True)
serie = q(
    f"""
    select t.data, t.eh_periodo_junino,
           sum(case when {faturado} then f.valor_liquido else 0 end) as faturamento,
           count(*) as pedidos
    from gold.fct_pedido f
    join gold.dim_tempo t using (sk_data)
    join gold.dim_status_pedido s using (sk_status_pedido)
    where {where}
    group by 1, 2 order by 1
    """,
    params,
)
serie["data"] = pd.to_datetime(serie["data"])
serie["faturamento"] = serie["faturamento"].astype(float)
if agregacao == "Semanal":
    serie = (
        serie.set_index("data")
        .resample("W-MON", label="left", closed="left")
        .agg({"faturamento": "sum", "pedidos": "sum", "eh_periodo_junino": "max"})
        .reset_index()
    )
fig = px.line(serie, x="data", y="faturamento", markers=agregacao == "Semanal")
fig.update_traces(line_color=VERDE, hovertemplate="%{x|%d/%m/%Y}<br>R$ %{y:,.2f}<extra></extra>")
junino = serie.loc[serie["eh_periodo_junino"].astype(bool), "data"]
if not junino.empty:
    fig.add_vrect(
        x0=junino.min(), x1=junino.max(), fillcolor=OCRE, opacity=0.15, line_width=0,
        annotation_text="Período junino", annotation_position="top left",
        annotation_font_color=OCRE,
    )  # fmt: skip
fig.update_yaxes(title=None, tickprefix="R$ ", tickformat=",.0f")
fig.update_xaxes(title=None, tickformat="%d/%m/%Y" if agregacao == "Diária" else "%d/%m")
st.plotly_chart(estilizar(fig, 360), use_container_width=True)

# --------------------------------------------------------------------------------------------
# 3. Pedidos por hora e 4. Canais
# --------------------------------------------------------------------------------------------

col_hora, col_canal = st.columns(2)

with col_hora:
    st.subheader("Pedidos por hora do dia")
    horas = q(
        f"""
        select h.hora,
               case when h.eh_pico then 'Em horário de pico' else 'Fora do pico' end as faixa,
               count(*) as pedidos
        from gold.fct_pedido f join gold.dim_hora h using (sk_hora)
        where {where} and h.hora is not null
        group by 1, 2 order by 1
        """,
        params,
    )
    horas["hora_rotulo"] = horas["hora"].map(lambda h: f"{int(h):02d}h")
    fig = px.bar(
        horas, x="hora_rotulo", y="pedidos", color="faixa",
        color_discrete_map={"Em horário de pico": OCRE, "Fora do pico": VERDE},
        category_orders={
            "faixa": ["Fora do pico", "Em horário de pico"],
            "hora_rotulo": sorted(horas["hora_rotulo"].unique()),
        },
    )  # fmt: skip
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None)
    st.plotly_chart(estilizar(fig), use_container_width=True)
    st.caption("Picos: 11h30–14h e 18h–20h30 (definição de `dim_hora`).")

with col_canal:
    st.subheader("Canais: digital × presencial")
    canais = q(
        f"""
        select c.nome_canal, c.tipo_canal, count(*) as pedidos,
               sum(case when {faturado} then f.valor_liquido else 0 end) as faturamento
        from gold.fct_pedido f
        join gold.dim_canal c using (sk_canal)
        join gold.dim_status_pedido s using (sk_status_pedido)
        where {where}
        group by 1, 2 order by faturamento desc
        """,
        params,
    )
    canais["faturamento"] = canais["faturamento"].astype(float)
    canais["canal"] = canais["nome_canal"].map(ROTULO_CANAL)
    canais["tipo"] = canais["tipo_canal"].str.capitalize()
    fig = px.bar(
        canais, x="canal", y="faturamento", color="tipo", text="pedidos",
        color_discrete_map={"Digital": VERDE, "Presencial": OCRE},
    )  # fmt: skip
    fig.update_traces(
        texttemplate="%{text:,} ped.", textposition="outside", cliponaxis=False,
        hovertemplate="%{x}<br>R$ %{y:,.2f}<extra></extra>",
    )  # fmt: skip
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None, tickprefix="R$ ", tickformat=",.0f")
    st.plotly_chart(estilizar(fig), use_container_width=True)
    st.caption("Barras: faturamento líquido; rótulos: pedidos do canal.")

# --------------------------------------------------------------------------------------------
# 5. Ranking por unidade
# --------------------------------------------------------------------------------------------

st.subheader("Ranking por unidade")
ranking = q(
    f"""
    select u.id_unidade,
           count(*) as pedidos,
           sum(case when {faturado} then f.valor_liquido else 0 end) as faturamento,
           sum(case when {faturado} then 1 else 0 end) as faturados,
           avg(case when f.sk_cliente <> -1 then 1.0 else 0.0 end) as identificados
    from gold.fct_pedido f
    join gold.dim_unidade u using (sk_unidade)
    join gold.dim_status_pedido s using (sk_status_pedido)
    where {where}
    group by 1
    """,
    params,
)
ranking = ranking.merge(dim_unidade[["id_unidade", "rotulo", "cidade", "uf"]], on="id_unidade")
ranking["faturamento"] = ranking["faturamento"].astype(float)
ranking["ticket"] = ranking["faturamento"] / ranking["faturados"].where(ranking["faturados"] > 0)
ranking = ranking.sort_values("faturamento", ascending=True)

col_rank = st.container()
col_tab = st.container()
with col_rank:
    fig = px.bar(ranking, x="faturamento", y="rotulo", orientation="h")
    fig.update_traces(marker_color=VERDE, hovertemplate="%{y}<br>R$ %{x:,.2f}<extra></extra>")
    fig.update_xaxes(title=None, tickprefix="R$ ", tickformat=",.0f")
    fig.update_yaxes(title=None)
    st.plotly_chart(estilizar(fig, 300), use_container_width=True)
with col_tab:
    tabela = ranking.sort_values("faturamento", ascending=False)
    st.dataframe(
        pd.DataFrame(
            {
                "Unidade": tabela["rotulo"],
                "Cidade/UF": tabela["cidade"] + "/" + tabela["uf"],
                "Pedidos": tabela["pedidos"].map(inteiro),
                "Faturamento": tabela["faturamento"].map(brl),
                "Ticket médio": tabela["ticket"].map(lambda v: brl(v) if pd.notna(v) else "—"),
                "Cliente identif.": tabela["identificados"].map(percentual),
            }
        ),
        hide_index=True,
        use_container_width=True,
    )

# --------------------------------------------------------------------------------------------
# 6. Pagamentos e 7. Status
# --------------------------------------------------------------------------------------------

st.subheader("Pagamentos")
col_p1, col_p2, col_p3 = st.columns(3)

resultado = q(
    f"select resultado, count(*) as tentativas from gold.fct_tentativa_pagamento f "
    f"where {where} group by 1",
    params,
)
with col_p1:
    fig = px.bar(
        resultado,
        x="resultado",
        y="tentativas",
        color="resultado",
        title="Tentativas por resultado",
        color_discrete_map={"APROVADO": VERDE, "RECUSADO": VERMELHO},
    )  # fmt: skip
    fig.update_xaxes(
        title=None, ticktext=["Aprovado", "Recusado"], tickvals=["APROVADO", "RECUSADO"]
    )
    fig.update_yaxes(title=None)
    fig.update_layout(showlegend=False)
    st.plotly_chart(estilizar(fig), use_container_width=True)

forma = q(
    f"""
    select p.nome_forma_pagamento as forma,
           avg(case when f.resultado = 'RECUSADO' then 1.0 else 0.0 end) as taxa
    from gold.fct_tentativa_pagamento f
    join gold.dim_forma_pagamento p using (sk_forma_pagamento)
    where {where} group by 1 order by taxa desc
    """,
    params,
)
forma["forma"] = forma["forma"].map(ROTULO_FORMA)
with col_p2:
    fig = px.bar(forma, x="forma", y="taxa", title="Taxa de recusa por forma de pagamento")
    fig.update_traces(
        marker_color=VERMELHO, texttemplate="%{y:.1%}", textposition="outside", cliponaxis=False,
        hovertemplate="%{x}<br>%{y:.1%}<extra></extra>",
    )  # fmt: skip
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None, tickformat=".0%")
    st.plotly_chart(estilizar(fig), use_container_width=True)

motivos = q(
    f"""
    select f.motivo_recusa as motivo, count(*) as recusas
    from gold.fct_tentativa_pagamento f
    where {where} and f.resultado = 'RECUSADO' and f.motivo_recusa is not null
    group by 1 order by recusas desc limit 6
    """,
    params,
)
motivos["motivo"] = motivos["motivo"].str.replace(" (simulação)", "", regex=False)
with col_p3:
    fig = px.bar(
        motivos.sort_values("recusas"), x="recusas", y="motivo", orientation="h",
        title="Principais motivos de recusa",
    )  # fmt: skip
    fig.update_traces(marker_color=CINZA)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None)
    st.plotly_chart(estilizar(fig), use_container_width=True)

st.subheader("Status atual dos pedidos")
status = q(
    f"""
    select s.nome_status_pedido as status, s.ordem_fluxo, count(*) as pedidos
    from gold.fct_pedido f join gold.dim_status_pedido s using (sk_status_pedido)
    where {where} group by 1, 2 order by 2
    """,
    params,
)
status["rotulo"] = status["status"].map(ROTULO_STATUS)
fig = px.bar(status, x="rotulo", y="pedidos", text="pedidos")
fig.update_traces(
    marker_color=[VERMELHO if s == "CANCELADO" else VERDE for s in status["status"]],
    texttemplate="%{text:,}", textposition="outside", cliponaxis=False,
)  # fmt: skip
fig.update_xaxes(title=None)
fig.update_yaxes(title=None)
st.plotly_chart(estilizar(fig, 300), use_container_width=True)

# --------------------------------------------------------------------------------------------
# Rodapé
# --------------------------------------------------------------------------------------------

st.divider()
st.caption(
    "Nota: a gold ainda não tem o nome das unidades (lacuna documentada: falta o evento de "
    "cadastro de unidade). Os nomes, cidades e UFs exibidos vêm de "
    "`dashboard/unidades_mockup.csv`, "
    "um mapeamento FICTÍCIO usado como paliativo até esse evento existir. "
    f"Fonte: gold do DuckDB (somente leitura). Gerado em {date.today():%d/%m/%Y}."
)
