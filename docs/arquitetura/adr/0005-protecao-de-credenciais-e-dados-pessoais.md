# ADR 0005 - Proteção de credenciais e dados pessoais

- **Status:** aceita
- **Data:** 2026-11-02

## Contexto

O repositório será público. Credenciais ou dados pessoais não podem aparecer nele, nem nos registros do uso de IA.

## Decisão

- `.env` fora do git (`.gitignore`); `.env.example` apenas com valores fictícios.
- Senha do banco local **aleatória**, gerada por `make setup` (`secrets.token_urlsafe`) e nunca impressa.
- Configuração lida de variáveis de ambiente; senha como `SecretStr`; logs nunca imprimem segredos.
- **Verificador de segredos** (`scripts/verificar_segredos.py`) no hook de pre-commit e na CI: chaves privadas, tokens conhecidos, atribuições de senha literal, arquivos `.env` e termos privados locais (`.registro-ia.local`, ignorado pelo git).
- Identidade git com e-mail **noreply**.
- **Redação** dos registros de IA antes de versioná-los.

## Alternativas consideradas

- Ferramentas de terceiros (gitleaks, trufflehog): mais completas, mas adicionam dependência; o verificador próprio é simples e auditável, e pode ser complementado depois.
- Gerenciador de segredos externo: excessivo para o escopo acadêmico.

## Consequências

- (+) Defesa em camadas: ignorar, verificar localmente e verificar na CI.
- (-) A detecção de senha literal é heurística (pode ter falsos positivos/negativos); linhas legítimas podem ser marcadas com `segredos:permitir`.
- (-) O hook só vale após `make setup`; a CI é a rede de segurança final.

**Autoria da decisão:** **requisito humano**; solução proposta pela IA.
