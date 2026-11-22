# dashboard/ - painel de vendas (mockup)

Painel Streamlit + Plotly sobre a **gold** do DW simulado (DuckDB, somente leitura). Os dados são
**fictícios**, gerados por simulação (`make dw-simulado`); serve para apresentação.

```bash
make dw-simulado      # gera o DW simulado (obrigatório antes)
make dashboard        # sobe o painel em http://127.0.0.1:8501 (DASHBOARD_PORT)
make dashboard-down   # derruba
make dashboard-lock   # regenera requirements.lock (só ao mudar requirements.in)
```

- Só SQL sobre `gold.*`; nunca lê o bronze. O `duckdb` tem a mesma versão do analytics (1.5.6).
- Imagem Python 3.14.10 (há wheels de streamlit, pandas, pyarrow e duckdb para 3.14), usuário
  não-root, porta publicada só em 127.0.0.1 e `./data` montado somente leitura.
- `unidades_mockup.csv`: mapeamento id -> nome FICTÍCIO das unidades. É um paliativo: a gold ainda
  não tem o nome das unidades (falta o evento de cadastro de unidade).
- Capturas: `scripts/evidencias/capturar_dashboard.py` (saída em `docs/dados/evidencias/`).
