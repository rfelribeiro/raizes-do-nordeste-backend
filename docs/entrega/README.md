# Documento de entrega

O trabalho é entregue como **PDF único**, em normas ABNT, com o nome `<RU>_Projeto_Back_End.PDF` (roteiro da trilha, L411–L418).

| Arquivo | Papel |
|---|---|
| [documento-principal.md](documento-principal.md) | Fonte do texto, seção a seção. Cada seção indica o que o roteiro exige, qual artefato do repositório a alimenta, o status e a autoria |
| `capa.local.yaml` | Dados da capa (nome, RU, polo, semestre, professor). **Fica fora do git**: o repositório é público |
| `saida/` | `.docx` e `.pdf` gerados. Fora do git |

## Fluxo

1. O conteúdo é escrito aos poucos no Markdown, a partir dos artefatos já versionados (`docs/requisitos`, `docs/modelagem`, `docs/api`, `docs/testes`, `docs/uso-de-ia`).
2. A conversão Markdown → `.docx` com um modelo de estilos ABNT (fonte 12, espaçamento 1,5, margens 3/2/3/2 cm) e depois → PDF é definida quando o texto estiver maduro, sempre por um caminho reproduzível (Docker).
3. Ajustes finos de diagramação (capa, folha de rosto, sumário) são feitos no `.docx` antes do PDF final.
