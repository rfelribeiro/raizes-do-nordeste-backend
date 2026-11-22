# Apresentação final: Raízes do Nordeste

Apresentação em HTML (20 slides, 16:9) para gravar o vídeo de 10 a 15 minutos. Tese: **comprar o que é commodity, integrar o que é crítico, construir só o que diferencia.** Identidade visual "Nordeste": xilogravura de cordel (SVG feito à mão), chita e papel de cordel.

## Como abrir

- Duplo clique em `index.html` (funciona por `file://`, sem servidor), ou
- `python3 -m http.server -d docs/apresentacao 8000` e abra `http://localhost:8000/`.

Só as fontes (Google Fonts: Alfa Slab One, Bitter, JetBrains Mono) vêm da internet; sem rede o navegador usa fontes locais de reserva (serifadas).

## Atalhos

| Tecla | Ação |
|---|---|
| Seta direita, seta para baixo, espaço, PageDown, Enter | próximo slide |
| Seta esquerda, seta para cima, PageUp, Backspace | slide anterior |
| Home / End | primeiro / último slide |
| F | tela cheia |
| N | mostra ou esconde as notas do apresentador (escondidas por padrão) |
| `#5` na URL | abre direto no slide 5 |

Para exportar em PDF (um slide por página): imprima pelo Chrome, destino "Salvar como PDF", sem margens e com "Gráficos de plano de fundo" ligado.

## Dados de mercado e contagens (`montar.py`)

Como o arquivo abre por `file://` (onde `fetch` falha), os dados entram por `<script src>`. O script lê os dados e gera `dados/mercado.js`:

```bash
python3 docs/apresentacao/montar.py
```

- `dados/mercado.json` (pesquisa de mercado: matriz por capacidade, TCO, roadmap) vira `window.MERCADO`, usado nos slides 14, 15 e 17. Sem esse arquivo, o script usa `dados/mercado-exemplo.json`, marcado como PENDENTE.
- `docs/uso-de-ia/decisoes.md` vira `window.DECISOES`: as contagens de decisões por origem (humana, conjunta, IA) do gráfico do slide 13. **Rode `montar.py` de novo antes de gravar**, pois novas decisões mudam os números.
- `docs/dados/evidencias/dashboard-*.png` vira `window.DASHBOARD`: se existirem, o slide 12 mostra as capturas do painel; senão, mostra o espaço reservado (`data-pendente="dashboard"`).

`dados/mercado.js` é gerado; não edite à mão.

## Capturas de conferência

`capturar.py` gera `previas/slide-NN.png` em 1920x1080 (pasta ignorada pelo git). Comando na raiz do repositório:

```bash
docker run --rm --user "$(id -u)" -e HOME=/tmp -v "$PWD":/work -w /work \
  mcr.microsoft.com/playwright/python:v1.49.1-noble \
  sh -c 'pip install -q --user playwright==1.49.1 && python3 docs/apresentacao/capturar.py'
```

## Dicas de gravação

1. Abra no Chrome ou Firefox, tecla **F** para tela cheia, resolução de captura **1920x1080**. A apresentação escala sozinha para qualquer tela.
2. Mantenha as notas **escondidas** (tecla N) durante a gravação; use-as só nos ensaios, ou numa segunda tela.
3. Ensaie com `#N` na URL para pular para um trecho. Cada slide tem de 3 a 6 frases de roteiro nas notas: adapte à sua voz.
4. Rode `python3 docs/apresentacao/montar.py` antes de gravar, para as contagens do slide 13 e os dados de mercado estarem atualizados.
5. Para a demonstração ao vivo (Swagger e Postman), suba o ambiente antes: `make up`, `make seed`.

## Declaração de apoio da IA

Esta apresentação foi feita com apoio da IA (Claude Code, modelo Sonnet), a partir da tese, da estrutura e do conteúdo definidos pelo autor (D-037) e dos fatos do próprio repositório (números de testes, arquitetura, modelagem, decisões). Os ornamentos de xilogravura e a chita são SVG originais, desenhados para este trabalho, sem copiar obras de artistas nem marcas. As falas são sugestões: o autor se apresenta e narra com as próprias palavras. O uso de IA no trabalho está declarado e detalhado em [`docs/uso-de-ia/`](../uso-de-ia/README.md).
