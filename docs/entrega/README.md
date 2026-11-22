# Documento de entrega

O trabalho é entregue como **PDF único**, em normas ABNT, com o nome `<RU>_Projeto_Back_End.PDF` (roteiro da trilha, L411–L418).

| Arquivo | Papel |
|---|---|
| [documento-principal.md](documento-principal.md) | Fonte do texto, seção a seção. Cada seção indica o que o roteiro exige, qual artefato do repositório a alimenta, o status e a autoria |
| `capa.local.yaml` | Dados da capa (nome, RU, polo, semestre, professor). **Fica fora do git**: o repositório é público |
| `saida/` | `.docx` e `.pdf` gerados. Fora do git |

## Fluxo

1. O conteúdo é escrito aos poucos no Markdown, a partir dos artefatos já versionados (`docs/requisitos`, `docs/modelagem`, `docs/api`, `docs/testes`, `docs/uso-de-ia`).
2. `make documento` gera `docs/entrega/saida/<RU>_Projeto_Back_End.docx` e `.PDF` (extensão em maiúsculas, como pede o roteiro). O RU e os demais dados da capa vêm de `capa.local.yaml`; nada disso fica no código versionado. O Markdown-fonte não é alterado.

### Ferramentas (todas em contêiner, com versão fixa; código em `scripts/entrega/`)

| Etapa | Ferramenta |
|---|---|
| Pré e pós-processamento | `python:3.14.10-slim` com `python-docx` 1.1.2 e `pyyaml` 6.0.2 (instalados em `saida/.pylibs`, sem tocar nos locks do projeto) |
| Diagramas Mermaid → PNG | `minlag/mermaid-cli:11.4.2` (fundo branco, escala 2) |
| Markdown → .docx | `pandoc/core:3.6.4` com um `reference.docx` de estilos ABNT gerado por `gerar_referencia.py` |
| .docx → PDF | LibreOffice headless (`libreoffice-writer` do Ubuntu 24.04, ver `Dockerfile.libreoffice`), com fontes Liberation e Carlito (métricas de Arial, Times e Calibri) |

### O que cada etapa faz

- **Pré-processamento** (`preprocessar.py`): copia o texto para `saida/documento.md` removendo os comentários HTML, o bloco YAML e os capítulos "Capa e folha de rosto" e "Sumário" (gerados pelo pipeline); coloca os títulos de seção primária em maiúsculas; troca cada bloco `mermaid` por um PNG sem legenda (a legenda já está no texto) com largura limitada à área útil; ajusta o tamanho das capturas existentes.
- **Pandoc**: converte para `.docx` sem numeração automática de títulos (a numeração já está no texto) e sem figuras com legenda automática.
- **Pós-processamento** (`posprocessar.py`): insere capa e folha de rosto a partir de `capa.local.yaml`; insere o sumário como campo TOC do Word (níveis 1 e 2); cria seções do Word para que a numeração conte desde a folha de rosto, mas só apareça (canto superior direito) a partir da Introdução; aplica os estilos de legenda e fonte (tamanho 10, espaçamento simples), centraliza títulos sem indicativo numérico (Referências e Apêndices), formata as tabelas (bordas simples, largura útil, cabeçalho repetido) e coloca em página paisagem as tabelas com 10 colunas ou mais (Tabela 23).
- **PDF** (`converter_pdf.py`): o LibreOffice abre o `.docx`, atualiza o sumário duas vezes (a paginação muda ao preencher o índice) e exporta o PDF.

A formatação segue a ABNT NBR 14724: A4, margens 3/2/3/2 cm, Arial 12, espaçamento 1,5, recuo de 1,25 cm. Ao abrir o `.docx` no Word, aceite atualizar os campos para recalcular o sumário.
