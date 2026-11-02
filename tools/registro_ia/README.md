# Registro de conversas com IA

Exporta cada conversa do Claude Code (sessão principal + subagentes) para Markdown em
`docs/uso-de-ia/conversas/`, com índice em `README.md` nessa pasta. Serve de evidência do uso de IA
(ferramenta, prompts e decisões humanas).

## Como funciona

- `exportar_conversas.py` lê as transcrições brutas (`~/.claude/projects/<projeto>/*.jsonl`) e gera um
  arquivo por sessão: `AAAA-MM-DD_HHMM_<id8>.md`. Cada execução regenera tudo (idempotente).
- Como hook (eventos Stop e SubagentStop) recebe JSON no stdin (`transcript_path`, `session_id`).
- Nunca interrompe o Claude Code: erros vão ao stderr e o código de saída é sempre 0.
- Exporta: prompts humanos (inclusive os enviados durante o turno), respostas visíveis da IA, chamadas
  de ferramenta em linha compacta, prompts completos de subagentes e decisões humanas
  (`AskUserQuestion`). Não exporta raciocínio (thinking), resultados de ferramentas nem conteúdo de
  arquivos (está no git).

## Uso manual

```bash
python3 tools/registro_ia/exportar_conversas.py --todas
python3 tools/registro_ia/exportar_conversas.py --sessao <session_id>
python3 -m unittest discover -s tools/registro_ia
```

## O que é redigido

Blocos injetados pelo sistema/IDE (`<system-reminder>`, `<ide_*>`, etc.); `$HOME` vira `~`; usuário do
SO, hostname, e-mails, IPv4 (exceto 127.0.0.1 e 0.0.0.0), MAC e tokens/segredos (chaves `sk-`, GitHub,
AWS, Slack, JWT, `Bearer`, `password=`/`token=` etc.) viram marcadores como `<usuario>`, `<email>`,
`<segredo>`.

## Termos pessoais adicionais

Crie `.registro-ia.local` na raiz do projeto (já está no `.gitignore`, nunca versionar): um termo por
linha, `#` inicia comentário, sem distinção de maiúsculas. Os termos (mais longos primeiro) viram
`<redigido>`. Depois de alterar a lista, rode `--todas` para regenerar os arquivos.
