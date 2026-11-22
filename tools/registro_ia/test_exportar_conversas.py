"""Testes do exportador de conversas (somente dados fictícios)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import exportar_conversas as ex

SCRIPT = Path(ex.__file__)


def linha(**kw):
    return kw


class TestLimpeza(unittest.TestCase):
    def test_remove_blocos_injetados(self):
        t = ("<system-reminder>\nsegredo do sistema\n</system-reminder>\n"
             "<ide_opened_file>arq.py</ide_opened_file>\nOlá, faça X.\n"
             "<command-name>/foo</command-name>")
        self.assertEqual(ex.limpar_usuario(t), "Olá, faça X.")

    def test_mantem_tag_no_meio_da_linha(self):
        self.assertIn("<b>x</b>", ex.limpar_usuario("use <b>x</b> aqui"))

    def test_linhas_de_sistema(self):
        t = "The user sent a new message while you were working:\nOi\n"
        self.assertEqual(ex.limpar_usuario(t), "Oi")


class TestRedacao(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self.tmp.name)
        (self.raiz / ex.ARQ_TERMOS).write_text("# c\nTermoSecreto\nTermoSecreto Longo\n", encoding="utf-8")
        self.R = ex.Redator(self.raiz, home="/home/fulano", usuario="fulano", host="maqfake")

    def tearDown(self):
        self.tmp.cleanup()

    def test_basicos(self):
        t = self.R("mail a.b@exemplo.com em /home/fulano/x host maqfake ip 10.1.2.3 e 127.0.0.1 mac aa:bb:cc:dd:ee:ff")
        self.assertIn("<email>", t)
        self.assertIn("~/x", t)
        self.assertIn("<host>", t)
        self.assertIn("<ip>", t)
        self.assertIn("127.0.0.1", t)
        self.assertIn("<mac>", t)
        self.assertNotIn("fulano", t)

    def test_tokens(self):
        t = self.R("sk-ant-abc123_x ghp_" + "a" * 25 + " Bearer xyz.1 password=abc senha=zzz")
        self.assertNotIn("abc123", t)
        self.assertNotIn("xyz", t)
        self.assertNotIn("zzz", t)
        self.assertGreaterEqual(t.count("<segredo>"), 4)

    def test_segredo_em_json(self):
        t = self.R('-d \'{"login":"x","senha":"Qwe@123"}\' e {\\"accessToken\\": \\"abc.def\\"}')
        self.assertNotIn("Qwe@123", t)
        self.assertNotIn("abc.def", t)
        self.assertIn('"senha":"<segredo>"', t)

    def test_termo_local_mais_longo_primeiro(self):
        t = self.R("veja termosecreto longo e TERMOSECRETO")
        self.assertEqual(t, "veja <redigido> e <redigido>")

    def test_caminho_relativo(self):
        self.assertEqual(self.R.caminho(str(self.raiz / "a" / "b.py")), "a/b.py")


class TestExportacao(unittest.TestCase):
    def _montar(self, d: Path):
        sid = "abcdef12-0000-0000-0000-000000000000"
        base = {"sessionId": sid, "isSidechain": False, "version": "9.9.9"}
        ev = [
            linha(type="user", timestamp="2030-01-01T10:00:00Z", origin={"kind": "human"}, **base,
                  message={"role": "user", "content": [
                      {"type": "text", "text": "<browser_instruction>\nlixo\n</browser_instruction>"},
                      {"type": "text", "text": "Prompt fictício inicial"}]}),
            linha(type="assistant", timestamp="2030-01-01T10:00:05Z", **base,
                  message={"id": "m1", "model": "modelo-x", "content": [
                      {"type": "thinking", "thinking": "oculto"},
                      {"type": "text", "text": "Resposta visível"},
                      {"type": "tool_use", "id": "t1", "name": "Bash",
                       "input": {"command": "ls", "description": "Listar"}},
                      {"type": "tool_use", "id": "t2", "name": "Agent",
                       "input": {"description": "Sub", "prompt": "PROMPT-SUB", "model": "haiku",
                                 "subagent_type": "general-purpose"}},
                      {"type": "tool_use", "id": "t3", "name": "AskUserQuestion",
                       "input": {"questions": [{"header": "Stack", "question": "Qual?",
                                                "options": [{"label": "A", "description": "da"}]}]}}]}),
            linha(type="user", timestamp="2030-01-01T10:00:06Z", **base,
                  toolUseResult={"answers": {"Qual?": "A"}},
                  message={"role": "user", "content": [
                      {"type": "tool_result", "tool_use_id": "t3", "content": "ok"},
                      {"type": "tool_result", "tool_use_id": "t1", "content": "SAIDA-OCULTA", "is_error": True}]}),
            linha(type="attachment", timestamp="2030-01-01T10:01:00Z", **base,
                  attachment={"type": "queued_command", "origin": {"kind": "human"},
                              "timestamp": "2030-01-01T10:01:00Z",
                              "prompt": [{"type": "text", "text": "Mensagem durante o turno"}]}),
        ]
        (d / f"{sid}.jsonl").write_text("\n".join(json.dumps(e) for e in ev) + "\nlixo{\n", encoding="utf-8")
        sub = d / sid / "subagents"
        sub.mkdir(parents=True)
        (sub / "agent-aaaa1111bbbb.meta.json").write_text(json.dumps(
            {"agentType": "general-purpose", "description": "Sub", "toolUseId": "t2", "model": "haiku"}))
        sb = {"sessionId": sid, "isSidechain": True}
        (sub / "agent-aaaa1111bbbb.jsonl").write_text("\n".join(json.dumps(e) for e in [
            linha(type="user", timestamp="2030-01-01T10:00:10Z", **sb,
                  message={"role": "user", "content": "PROMPT-SUB"}),
            linha(type="assistant", timestamp="2030-01-01T10:00:11Z", **sb,
                  message={"id": "s1", "model": "haiku-x", "content": [{"type": "text", "text": "feito"}]})]))
        return sid

    def test_fluxo_completo(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sid = self._montar(tmp)
            R = ex.Redator(tmp, home="/home/fulano", usuario="fulano", host="maqfake", termos=[])
            saida = tmp / "out"
            dest = ex.exportar_sessao(tmp / f"{sid}.jsonl", saida, R)
            ex.gerar_indice(saida)
            md = dest.read_text(encoding="utf-8")
            self.assertIn("Prompt fictício inicial", md)
            self.assertNotIn("lixo", md)
            self.assertNotIn("oculto", md)
            self.assertNotIn("SAIDA-OCULTA", md)
            self.assertIn("🧑 Humano (durante o turno)", md)
            self.assertIn("Mensagem durante o turno", md)
            self.assertIn("⚠️ erro", md)
            self.assertIn("🧭 **Decisão humana**", md)
            self.assertIn("Resposta do humano:** A", md)
            self.assertIn("PROMPT-SUB", md)
            self.assertIn("Prompt do agente principal", md)
            self.assertIn("Claude Code 9.9.9", md)
            self.assertIn("abcdef12", (saida / "README.md").read_text(encoding="utf-8"))

    def test_hook_json_invalido_nao_quebra(self):
        for entrada in ("{nao é json", "", "[]", '{"transcript_path": "/nao/existe.jsonl"}'):
            r = subprocess.run([sys.executable, str(SCRIPT)], input=entrada, text=True,
                               capture_output=True, timeout=20)
            self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
