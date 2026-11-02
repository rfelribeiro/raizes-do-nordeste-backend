"""Configuração global dos testes.

Define valores FICTÍCIOS para as variáveis obrigatórias quando o ambiente não as fornece
(ex.: rodando fora do compose), para que os testes unitários nunca dependam de segredos reais.
"""

import os

os.environ.setdefault("POSTGRES_DB", "raizes_teste")
os.environ.setdefault("POSTGRES_USER", "raizes_teste")
os.environ.setdefault("POSTGRES_PASSWORD", "senha_ficticia_de_teste")
