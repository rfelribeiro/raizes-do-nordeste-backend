#!/usr/bin/env python3
"""Exporta conversas do Claude Code (sessão principal + subagentes) para Markdown.

Uso:
  - Hook (Stop/SubagentStop): JSON no stdin com session_id/transcript_path/cwd.
  - CLI: ``--todas`` ou ``--sessao <id>``.

Só biblioteca padrão (Python >= 3.10). Nunca quebra o fluxo do Claude Code:
qualquer erro vai para o stderr e o código de saída é sempre 0.
Todo texto exportado passa por redação de dados pessoais (ver README.md).
"""
from __future__ import annotations

import datetime as dt
import getpass
import json
import os
import re
import socket
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / "docs" / "uso-de-ia" / "conversas"
ARQ_TERMOS = ".registro-ia.local"
MAX_CMD = 600
MAX_RESP = 1500

# --------------------------------------------------------------------------
# Redação
# --------------------------------------------------------------------------


class Redator:
    """Aplica a redação de dados pessoais a qualquer texto exportado."""

    def __init__(self, raiz: Path = RAIZ, home: str | None = None,
                 usuario: str | None = None, host: str | None = None,
                 termos: list[str] | None = None):
        self.raiz = str(raiz)
        self.home = home if home is not None else os.path.expanduser("~")
        try:
            self.usuario = usuario if usuario is not None else getpass.getuser()
        except Exception:
            self.usuario = ""
        try:
            self.host = host if host is not None else socket.gethostname()
        except Exception:
            self.host = ""
        if termos is None:
            termos = carregar_termos(raiz / ARQ_TERMOS)
        self.termos = sorted({t for t in termos if t}, key=len, reverse=True)
        self._marcas: list[str] = []

    # Marcadores privados evitam que um passo posterior corrompa um anterior.
    def _m(self, rotulo: str) -> str:
        self._marcas.append(rotulo)
        return f"{len(self._marcas) - 1}"

    def _sub(self, padrao: re.Pattern, rotulo: str, texto: str) -> str:
        return padrao.sub(lambda _m: self._m(rotulo), texto)

    def __call__(self, texto: str) -> str:
        if not texto:
            return texto
        self._marcas = []
        t = texto
        # tokens e segredos
        t = re.sub(r"(?i)\b(password|senha|secret|token|api_key)=\S+",
                   lambda m: m.group(1) + "=" + self._m("<segredo>"), t)
        # mesmo segredo em JSON (ex.: corpo de login em comandos curl): "senha":"..."
        t = re.sub(r'(?i)("(?:password|senha|secret|token|api_key|accessToken)\\?"\s*:\s*\\?")'
                   r'([^"\\]+)',
                   lambda m: m.group(1) + self._m("<segredo>"), t)
        for pad in (r"sk-ant-[\w-]+", r"sk-[A-Za-z0-9]{20,}", r"gh[pousr]_[A-Za-z0-9]{20,}",
                    r"github_pat_\w+", r"AKIA[0-9A-Z]{16}", r"xox[baprs]-[\w-]+",
                    r"eyJ[\w-]+\.[\w-]+\.[\w-]+"):
            t = self._sub(re.compile(pad), "<segredo>", t)
        t = re.sub(r"Bearer\s+\S+", lambda _m: self._m("<segredo>"), t)
        # e-mail, MAC, IPv4
        t = self._sub(re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "<email>", t)
        t = self._sub(re.compile(r"\b[0-9A-Fa-f]{2}(?:[:-][0-9A-Fa-f]{2}){5}\b"), "<mac>", t)
        t = re.sub(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])",
                   lambda m: m.group(0) if m.group(0) in ("127.0.0.1", "0.0.0.0")
                   else self._m("<ip>"), t)
        # home antes dos termos locais, para que o caminho vire "~" e não "/home/<redigido>"
        if self.home and self.home not in ("/", ""):
            t = t.replace(self.home, "~")
        # termos locais (mais longos primeiro)
        for termo in self.termos:
            t = re.sub(re.escape(termo), lambda _m: self._m("<redigido>"), t, flags=re.I)
        # usuário, host
        for valor, rotulo in ((self.usuario, "<usuario>"), (self.host, "<host>")):
            if valor and len(valor) >= 2:
                t = re.sub(r"(?<![A-Za-z0-9])" + re.escape(valor) + r"(?![A-Za-z0-9])",
                           lambda _m, r=rotulo: self._m(r), t, flags=re.I)
        return re.sub("(\\d+)", lambda m: self._marcas[int(m.group(1))], t)

    def caminho(self, caminho: str) -> str:
        """Caminho relativo à raiz do projeto quando possível (depois redigido)."""
        if not caminho:
            return ""
        if caminho == self.raiz:
            return "."
        if caminho.startswith(self.raiz + os.sep):
            return self(caminho[len(self.raiz) + 1:])
        return self(caminho)

    def comando(self, cmd: str) -> str:
        return self(cmd.replace(self.raiz + os.sep, "").replace(self.raiz, "."))


def carregar_termos(arq: Path) -> list[str]:
    try:
        out = []
        for linha in arq.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#"):
                out.append(linha)
        return out
    except Exception:
        return []


# --------------------------------------------------------------------------
# Limpeza de blocos injetados
# --------------------------------------------------------------------------

BLOCO_XML = re.compile(r"^<([a-z][a-z0-9_-]*)(?:\s[^>\n]*)?>.*?</\1>[ \t]*\n?",
                       re.S | re.M)
LINHAS_SISTEMA = re.compile(
    r"^(The user sent a new message while you were working:|"
    r"This is how Claude Code surfaces messages.*|"
    r"IMPORTANT: After completing your current task, you MUST address.*)\s*$",
    re.M)


def limpar_usuario(texto: str) -> str:
    """Remove blocos <tag>...</tag> injetados pelo sistema/IDE."""
    anterior = None
    while anterior != texto:
        anterior = texto
        texto = BLOCO_XML.sub("", texto)
    texto = LINHAS_SISTEMA.sub("", texto)
    return re.sub(r"\n{3,}", "\n\n", texto).strip()


def texto_de_conteudo(c) -> str:
    if isinstance(c, str):
        return c
    partes = []
    if isinstance(c, list):
        for b in c:
            if isinstance(b, dict):
                if b.get("type") == "text":
                    partes.append(b.get("text", ""))
                elif b.get("type") == "image":
                    partes.append("[imagem omitida]")
            elif isinstance(b, str):
                partes.append(b)
    return "\n\n".join(p for p in partes if p)


# --------------------------------------------------------------------------
# Leitura e modelagem
# --------------------------------------------------------------------------


def ler_jsonl(caminho: Path) -> list[dict]:
    out = []
    try:
        with open(caminho, encoding="utf-8", errors="replace") as f:
            for linha in f:
                try:
                    o = json.loads(linha)
                    if isinstance(o, dict):
                        out.append(o)
                except Exception:
                    continue
    except Exception:
        pass
    return out


def parse_ts(s) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def hhmm(d: dt.datetime | None) -> str:
    return d.astimezone().strftime("%H:%M") if d else "--:--"


class Conversa:
    """Conversa (principal ou subagente) já interpretada."""

    def __init__(self, eventos: list[dict], subagente: bool = False):
        self.turnos: list[dict] = []
        self.modelos: set[str] = set()
        self.versao = ""
        self.msgs_ia: set = set()
        self.n_tools = 0
        self.n_humano = 0
        self.n_durante = 0
        self.tempos: list[dt.datetime] = []
        self._tools: dict[str, dict] = {}
        self._ia: dict | None = None
        self._subagente = subagente
        self._viu_prompt = False
        for i, ev in enumerate(eventos):
            try:
                self._evento(ev, i)
            except Exception:
                continue

    def _evento(self, ev: dict, i: int):
        tipo = ev.get("type")
        ts = parse_ts(ev.get("timestamp"))
        if ts and tipo in ("user", "assistant", "attachment"):
            self.tempos.append(ts)
        if ev.get("isSidechain") and not self._subagente:
            return
        if not self.versao and ev.get("version"):
            self.versao = str(ev["version"])
        if tipo == "attachment":
            a = ev.get("attachment") or {}
            if a.get("type") == "queued_command" and (a.get("origin") or {}).get("kind") == "human":
                texto = limpar_usuario(texto_de_conteudo(a.get("prompt")))
                if texto:
                    self._ia = None
                    self.n_durante += 1
                    self.turnos.append({"papel": "durante", "ts": parse_ts(a.get("timestamp")) or ts,
                                        "texto": texto})
        elif tipo == "user":
            self._usuario(ev, ts)
        elif tipo == "assistant":
            self._assistente(ev, ts)

    def _usuario(self, ev: dict, ts):
        msg = ev.get("message") or {}
        c = msg.get("content")
        if isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    self._resultado(b, ev.get("toolUseResult"))
            if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
                return
        if ev.get("isMeta"):
            return
        origem = ev.get("origin")
        if origem and origem.get("kind") != "human":
            return
        texto = limpar_usuario(texto_de_conteudo(c))
        if not texto:
            return
        self._ia = None
        if self._subagente:
            self.turnos.append({"papel": "agente_prompt" if not self._viu_prompt else "agente_msg",
                                "ts": ts, "texto": texto})
            self._viu_prompt = True
        else:
            self.n_humano += 1
            self.turnos.append({"papel": "humano", "ts": ts, "texto": texto})

    def _assistente(self, ev: dict, ts):
        msg = ev.get("message") or {}
        modelo = msg.get("model")
        if not modelo or modelo == "<synthetic>":
            return
        self.modelos.add(modelo)
        if msg.get("id"):
            self.msgs_ia.add(msg["id"])
        else:
            self.msgs_ia.add(ev.get("uuid"))
        if self._ia is None or self._ia["modelo"] != modelo:
            self._ia = {"papel": "ia", "ts": ts, "modelo": modelo, "itens": []}
            self.turnos.append(self._ia)
        c = msg.get("content")
        if isinstance(c, str):
            c = [{"type": "text", "text": c}]
        for b in c or []:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "text" and (b.get("text") or "").strip():
                self._ia["itens"].append({"k": "texto", "texto": b["text"].strip()})
            elif b.get("type") == "tool_use":
                self.n_tools += 1
                item = {"k": "tool", "nome": b.get("name", "?"), "input": b.get("input") or {},
                        "id": b.get("id"), "erro": False, "resultado": None, "dados": None}
                self._ia["itens"].append(item)
                if b.get("id"):
                    self._tools[b["id"]] = item

    def _resultado(self, b: dict, dados):
        item = self._tools.get(b.get("tool_use_id"))
        if not item:
            return
        if b.get("is_error"):
            item["erro"] = True
        if item["nome"] == "AskUserQuestion":
            item["resultado"] = texto_de_conteudo(b.get("content"))
            item["dados"] = dados


# --------------------------------------------------------------------------
# Renderização
# --------------------------------------------------------------------------


def cerca(texto: str) -> str:
    n = max([len(m) for m in re.findall(r"`+", texto)] + [2]) + 1
    return "`" * n


def bloco_codigo(texto: str, lang: str = "") -> str:
    c = cerca(texto)
    return f"{c}{lang}\n{texto}\n{c}"


def truncar(t: str, n: int) -> str:
    return t if len(t) <= n else t[:n].rstrip() + " … [truncado]"


def citar(texto: str) -> str:
    return "\n".join(("> " + l).rstrip() for l in texto.splitlines())


def neutralizar_titulos(texto: str) -> str:
    out, dentro = [], False
    for l in texto.splitlines():
        if l.lstrip().startswith("```"):
            dentro = not dentro
        if not dentro and re.match(r"#{1,6}\s", l):
            l = "**" + l.lstrip("# ").strip() + "**"
        out.append(l)
    return "\n".join(out)


def slug_sub(agent_id: str) -> str:
    return "sub-" + agent_id[:8]


def render_tool(it: dict, R: Redator, subs_por_tool: dict) -> str:
    nome, inp = it["nome"], it["input"]
    erro = " ⚠️ erro" if it["erro"] else ""
    if nome == "Bash":
        desc = R(str(inp.get("description") or "")).strip()
        cab = "🔧 Bash" + (f" — {desc}" if desc else "")
        return f"{cab}{erro}\n\n" + bloco_codigo(truncar(R.comando(str(inp.get("command", ""))), MAX_CMD), "bash")
    if nome in ("Read", "Grep", "Glob"):
        alvo = inp.get("file_path") or inp.get("pattern") or inp.get("path") or ""
        if nome == "Grep" and inp.get("path"):
            alvo = f"{inp.get('pattern', '')} ({R.caminho(str(inp['path']))})"
            alvo = R(alvo)
        else:
            alvo = R.caminho(str(alvo))
        return f"📖 {nome} — `{alvo}`{erro}"
    if nome in ("Write", "Edit", "NotebookEdit"):
        alvo = inp.get("file_path") or inp.get("notebook_path") or ""
        return f"✏️ {nome} — `{R.caminho(str(alvo))}`{erro}"
    if nome in ("Agent", "Task"):
        desc = R(str(inp.get("description", "")))
        cab = (f"🤝 Subagente — {desc} (tipo: {inp.get('subagent_type', 'general-purpose')}, "
               f"modelo: {inp.get('model') or 'padrão'}){erro}")
        prompt = R(str(inp.get("prompt", "")))
        c = cerca(prompt)
        corpo = f"{cab}\n\n<details>\n<summary>Prompt completo enviado ao subagente</summary>\n\n{c}text\n{prompt}\n{c}\n\n</details>"
        alvo = subs_por_tool.get(it["id"])
        if alvo:
            corpo += f"\n\nConversa do subagente: [{slug_sub(alvo)}](#{slug_sub(alvo)})"
        return corpo
    if nome == "AskUserQuestion":
        return render_ask(it, R)
    return f"🔧 {R(nome)}{erro}"


def render_ask(it: dict, R: Redator) -> str:
    inp = it["input"]
    dados = it["dados"] if isinstance(it["dados"], dict) else {}
    respostas = dados.get("answers") if isinstance(dados.get("answers"), dict) else {}
    linhas = ["🧭 **Decisão humana** (pergunta da IA e resposta do humano)", ""]
    for q in inp.get("questions", []) or []:
        if not isinstance(q, dict):
            continue
        linhas.append(f"- **{R(str(q.get('header', 'Pergunta')))}** — {R(str(q.get('question', '')))}")
        for o in q.get("options", []) or []:
            if isinstance(o, dict):
                d = f": {R(str(o['description']))}" if o.get("description") else ""
                linhas.append(f"  - opção **{R(str(o.get('label', '')))}**{d}")
        r = respostas.get(q.get("question"))
        if r is not None:
            linhas.append(f"  - **Resposta do humano:** {R(str(r))}")
    if not respostas:
        if it["resultado"]:
            linhas += ["", "**Resposta do humano (registro bruto):**", "",
                       citar(truncar(R(it["resultado"]), MAX_RESP))]
        else:
            linhas += ["", "_Resposta ainda não registrada no momento da exportação._"]
    if it["erro"]:
        linhas.append("⚠️ erro")
    return "\n".join(linhas)


def render_conversa(conv: Conversa, R: Redator, subs_por_tool: dict, nivel: str = "###") -> str:
    partes = []
    for t in conv.turnos:
        h = hhmm(t["ts"])
        p = t["papel"]
        if p == "humano":
            partes.append(f"{nivel} 🧑 Humano — {h}\n\n{citar(R(t['texto']))}")
        elif p == "durante":
            partes.append(f"{nivel} 🧑 Humano (durante o turno) — {h}\n\n{citar(R(t['texto']))}")
        elif p == "agente_prompt":
            partes.append(f"{nivel} 🤖➡️🤖 Prompt do agente principal — {h}\n\n"
                          f"<details>\n<summary>Ver prompt completo</summary>\n\n"
                          f"{cerca(R(t['texto']))}text\n{R(t['texto'])}\n{cerca(R(t['texto']))}\n\n</details>")
        elif p == "agente_msg":
            partes.append(f"{nivel} 🤖➡️🤖 Mensagem do agente principal — {h}\n\n{citar(R(t['texto']))}")
        else:
            corpo = []
            for it in t["itens"]:
                if it["k"] == "texto":
                    corpo.append(neutralizar_titulos(R(it["texto"])))
                else:
                    corpo.append(render_tool(it, R, subs_por_tool))
            if corpo:
                partes.append(f"{nivel} 🤖 IA ({R(t['modelo'])}) — {h}\n\n" + "\n\n".join(corpo))
    return "\n\n".join(partes)


# --------------------------------------------------------------------------
# Sessão completa
# --------------------------------------------------------------------------


def fmt_dur(seg: float) -> str:
    seg = int(seg)
    h, r = divmod(seg, 3600)
    m, s = divmod(r, 60)
    return f"{h}h{m:02d}min" if h else (f"{m}min{s:02d}s" if m else f"{s}s")


def exportar_sessao(transcript: Path, saida: Path = SAIDA, R: Redator | None = None) -> Path | None:
    R = R or Redator()
    transcript = Path(transcript)
    sid = transcript.stem
    ev = ler_jsonl(transcript)
    if not ev:
        return None
    principal = Conversa(ev)

    subs = []
    dir_subs = transcript.parent / sid / "subagents"
    if dir_subs.is_dir():
        for jl in sorted(dir_subs.glob("agent-*.jsonl")):
            aid = jl.stem[len("agent-"):]
            try:
                meta = json.loads(jl.with_suffix("").with_suffix(".meta.json").read_text(encoding="utf-8"))
            except Exception:
                meta = {}
            subs.append({"id": aid, "meta": meta, "conv": Conversa(ler_jsonl(jl), subagente=True)})
    subs.sort(key=lambda s: (s["conv"].tempos[0] if s["conv"].tempos else dt.datetime.max.replace(tzinfo=dt.timezone.utc)))
    subs_por_tool = {s["meta"].get("toolUseId"): s["id"] for s in subs if s["meta"].get("toolUseId")}

    tempos = list(principal.tempos)
    for s in subs:
        tempos += s["conv"].tempos
    ini, fim = (min(tempos), max(tempos)) if tempos else (None, None)
    modelos = set(principal.modelos)
    for s in subs:
        modelos |= s["conv"].modelos
    n_prompts = principal.n_humano + principal.n_durante
    n_tools = principal.n_tools + sum(s["conv"].n_tools for s in subs)
    n_resp = len(principal.msgs_ia) + sum(len(s["conv"].msgs_ia) for s in subs)
    ini_local = ini.astimezone() if ini else dt.datetime.now().astimezone()
    nome = f"{ini_local:%Y-%m-%d_%H%M}_{sid[:8]}.md"

    resumo = {"arquivo": nome, "data": f"{ini_local:%Y-%m-%d %H:%M}", "sessao": sid[:8],
              "modelos": sorted(modelos), "prompts": n_prompts, "subagentes": len(subs)}
    L = [f"<!-- resumo: {json.dumps(resumo, ensure_ascii=False)} -->",
         f"# Conversa com IA — sessão {sid[:8]}", "",
         f"- **Sessão:** `{sid[:8]}`",
         f"- **Início:** {ini_local:%Y-%m-%d %H:%M}"
         + (f" — **Fim:** {fim.astimezone():%Y-%m-%d %H:%M} — **Duração:** {fmt_dur((fim - ini).total_seconds())}" if ini else ""),
         f"- **Ferramenta:** Claude Code{(' ' + principal.versao) if principal.versao else ''}",
         f"- **Modelos usados:** {', '.join(sorted(R(m) for m in modelos)) or '—'}",
         f"- **Totais:** {principal.n_humano} prompts humanos"
         f" (+ {principal.n_durante} mensagens durante o turno), {n_resp} respostas da IA, "
         f"{n_tools} chamadas de ferramenta, {len(subs)} subagentes",
         "",
         "> Exportação automática (`tools/registro_ia/exportar_conversas.py`). Blocos de raciocínio (thinking), "
         "resultados de ferramentas e conteúdo de arquivos criados/editados não são exportados; "
         "dados pessoais são redigidos.",
         "", "## Linha do tempo", "", render_conversa(principal, R, subs_por_tool)]
    if subs:
        L += ["", "## Subagentes"]
        for s in subs:
            m = s["meta"]
            titulo = R(str(m.get("description") or m.get("agentType") or "subagente"))
            mod = ", ".join(sorted(R(x) for x in s["conv"].modelos)) or R(str(m.get("model", "—")))
            L += ["", f'<a id="{slug_sub(s["id"])}"></a>', "",
                  f"## 🤝 Subagente {s['id'][:8]} — {titulo}", "",
                  f"- Tipo: {R(str(m.get('agentType', '—')))} — Modelo: {mod} — "
                  f"{len(s['conv'].msgs_ia)} respostas, {s['conv'].n_tools} chamadas de ferramenta", "",
                  render_conversa(s["conv"], R, {}, "###")]
    saida.mkdir(parents=True, exist_ok=True)
    # nome pode mudar se o início mudar: remove versões antigas da mesma sessão
    for velho in saida.glob(f"*_{sid[:8]}.md"):
        if velho.name != nome:
            velho.unlink()
    destino = saida / nome
    tmp = destino.with_suffix(".tmp")
    tmp.write_text("\n".join(L).rstrip() + "\n", encoding="utf-8")
    os.replace(tmp, destino)
    return destino


def gerar_indice(saida: Path = SAIDA):
    linhas = []
    for md in sorted(saida.glob("*.md")):
        if md.name == "README.md":
            continue
        try:
            m = re.match(r"<!-- resumo: (.*) -->", md.read_text(encoding="utf-8").split("\n", 1)[0])
            r = json.loads(m.group(1))
            linhas.append((r["data"], f"| {r['data']} | `{r['sessao']}` | {', '.join(r['modelos']) or '—'} | "
                           f"{r['prompts']} | {r['subagentes']} | [{md.name}]({md.name}) |"))
        except Exception:
            continue
    corpo = ["# Registro de conversas com IA", "",
             "Índice gerado automaticamente por `tools/registro_ia/exportar_conversas.py`. "
             "Cada conversa com o Claude Code (sessão principal e subagentes) é exportada para Markdown, "
             "com dados pessoais redigidos.", "",
             "| Data | Sessão | Modelos | Nº de prompts humanos | Nº de subagentes | Link |",
             "|---|---|---|---|---|---|"] + [l for _, l in sorted(linhas)]
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "README.md").write_text("\n".join(corpo) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------
# Entrada
# --------------------------------------------------------------------------


def dir_transcricoes() -> Path:
    cod = re.sub(r"[^A-Za-z0-9]", "-", str(RAIZ))
    return Path.home() / ".claude" / "projects" / cod


def principal(argv: list[str]) -> None:
    transcritos: list[Path] = []
    if "--todas" in argv:
        transcritos = sorted(dir_transcricoes().glob("*.jsonl"))
    elif "--sessao" in argv:
        sid = argv[argv.index("--sessao") + 1]
        transcritos = [dir_transcricoes() / f"{sid}.jsonl"]
    elif not sys.stdin.isatty():
        dados = json.loads(sys.stdin.read() or "{}")
        tp = dados.get("transcript_path")
        if not tp and dados.get("session_id"):
            tp = str(dir_transcricoes() / f"{dados['session_id']}.jsonl")
        if not tp:
            return
        transcritos = [Path(tp)]
    else:
        print("Uso: exportar_conversas.py --todas | --sessao <id>  (ou JSON de hook no stdin)")
        return
    R = Redator()
    for t in transcritos:
        try:
            exportar_sessao(t, SAIDA, R)
        except Exception as e:
            print(f"registro_ia: falha ao exportar {t.name}: {type(e).__name__}", file=sys.stderr)
    gerar_indice(SAIDA)


def main() -> int:
    try:
        principal(sys.argv[1:])
    except BaseException as e:  # nunca quebrar o Claude Code
        print(f"registro_ia: erro: {type(e).__name__}: {str(e)[:120]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
