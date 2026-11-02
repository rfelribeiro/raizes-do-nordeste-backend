# Infraestrutura de desenvolvimento

Este documento registra o ambiente de desenvolvimento e o uso de ferramentas de inteligência artificial no projeto, conforme exigido pelo roteiro da disciplina, que pede a declaração da ferramenta de IA utilizada. Os dados foram coletados em **2026-11-02**. Informações pessoais e identificadores da máquina e da conta foram deliberadamente omitidos (ver seção 7).

## 1. Hardware

| Item | Valor |
|---|---|
| Fabricante / modelo | Samsung 550XDA (notebook) |
| CPU | Intel Core i5-1135G7 (11ª geração), 2,40 GHz |
| Núcleos / threads | 4 núcleos físicos / 8 threads (2 threads por núcleo) |
| Arquitetura | x86_64 |
| RAM | 14 GiB |
| Armazenamento | 931,5 GB, SSD NVMe |
| GPU | Intel Iris Xe Graphics (TigerLake-LP GT2), integrada |

## 2. Sistema operacional

| Item | Valor |
|---|---|
| Distribuição e versão | Ubuntu 26.04.1 LTS |
| Kernel | 7.0.0-38-generic (x86_64) |
| Ambiente gráfico / sessão | GNOME sobre Wayland |

## 3. IDE

| Item | Valor |
|---|---|
| Visual Studio Code | 1.143.1, instalado via snap |

Extensões relevantes:

| Extensão | Versão |
|---|---|
| Claude Code (`anthropic.claude-code`) | 2.1.314 |
| Python (`ms-python.python`) | 2026.10.0 |
| Pylance (`ms-python.vscode-pylance`) | 2026.4.1 |
| Python Debugger (`ms-python.debugpy`) | 2026.6.0 |
| Python Environments (`ms-python.vscode-python-envs`) | 1.40.0 |

Não há extensão do Docker instalada no VS Code (o Docker foi usado pela linha de comando).

## 4. Assistente de IA

| Ferramenta | Versão | Plano | Forma de uso |
|---|---|---|---|
| Claude Code (Anthropic) | CLI 2.1.316; extensão para VS Code 2.1.314 | Claude Pro (assinatura individual, cobrança mensal) | Dentro do VS Code (extensão oficial) e pela linha de comando (CLI) |

Modelos e papéis no projeto:

| Modelo | ID | Papel no projeto |
|---|---|---|
| Claude Opus 5.5 | `claude-opus-5-5` | Sessão principal: par de arquitetura com o humano, revisão, decisões propostas e integração |
| Claude Sonnet 5.5 | `claude-sonnet-5-5` | Subagente de custo intermediário para código "braçal" sob especificação |
| Claude Haiku 5.5 | `claude-haiku-5-5` | Subagente de menor custo para coleta e tarefas mecânicas (como esta coleta) |

**Motivo da divisão.** O plano Claude Pro possui cota de uso limitada. Por isso, o modelo mais caro foi reservado para decisões e revisão, e o trabalho repetitivo foi delegado a modelos menores. A divisão foi uma decisão do humano responsável pelo projeto.

## 5. Ferramentas de desenvolvimento

| Ferramenta | Versão |
|---|---|
| Python | 3.14.4 |
| Git | 2.53.0 |
| Docker | 29.8.1 |
| Docker Compose | v5.5.1 |
| Node.js | v24.19.0 |
| npm | 11.17.0 |
| jq | 1.8.1 |

## 6. Como estes dados foram coletados

A coleta foi feita por um subagente Claude Haiku 5.5, sob instrução do agente principal (Claude Opus 5.5), que revisou o resultado. A revisão humana está registrada no [inventário de artefatos](README.md#inventário-de-artefatos-produzidos-com-ia-trechos-aproveitados). O plano de assinatura foi verificado pelo agente principal lendo **somente** os campos de tipo de assinatura e de cobrança da configuração local do Claude Code, sem ler tokens nem dados de conta. Os comandos executados pelo subagente foram:

- `lscpu | grep -E 'Model name|^CPU\(s\)|Thread\(s\) per core|Core\(s\) per socket|Architecture'`
- `free -h | head -2`
- `lsblk -d -o SIZE,ROTA,TYPE,TRAN | grep disk`
- `lspci 2>/dev/null | grep -iE 'vga|3d|display' | sed 's/^[0-9a-f:.]* //'`
- `cat /sys/class/dmi/id/sys_vendor /sys/class/dmi/id/product_name 2>/dev/null`
- `grep -E '^(PRETTY_NAME|VERSION_ID)=' /etc/os-release`
- `uname -r -m`
- `echo "$XDG_CURRENT_DESKTOP / $XDG_SESSION_TYPE"`
- `code --version 2>/dev/null | head -1`
- `code --list-extensions --show-versions 2>/dev/null | grep -iE 'anthropic|python|docker|ms-python'`
- `which code`
- `claude --version`
- `python3 --version; git --version; docker --version; docker compose version 2>/dev/null; node --version 2>/dev/null; npm --version 2>/dev/null; jq --version`

## 7. Dados deliberadamente omitidos

Por questões de privacidade (Lei Geral de Proteção de Dados, LGPD) e por se tratar de um repositório público, **não** foram registrados:

- nome do host (hostname) da máquina;
- nome de usuário do sistema operacional e caminhos de diretórios pessoais;
- endereços de e-mail;
- números de série e identificadores de hardware (UUID, ID de máquina);
- identificadores de conta (de usuário, de organização e de assinatura do assistente de IA);
- dados de rede (endereços IP e MAC);
- credenciais e tokens de acesso.
