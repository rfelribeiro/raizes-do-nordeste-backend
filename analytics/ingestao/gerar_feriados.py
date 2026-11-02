"""Gera `seeds/feriados_nacionais.csv` (feriados nacionais do Brasil, 2024-2030).

Fixos + móveis calculados a partir da Páscoa (algoritmo gregoriano anônimo / Meeus-Jones-Butcher):
Carnaval (segunda e terça, 48 e 47 dias antes), Sexta-feira Santa (-2) e Corpus Christi (+60).
Carnaval é ponto facultativo pela lei federal, mas é tratado como feriado no comércio; mantenha
ou remova conforme a definição de negócio do autor.

Uso (a partir da raiz do repositório):
    python analytics/ingestao/gerar_feriados.py
"""

import csv
from datetime import date, timedelta
from pathlib import Path

ANO_INICIAL = 2024
ANO_FINAL = 2030
DESTINO = (
    Path(__file__).resolve().parents[1] / "dbt" / "raizes_dw" / "seeds" / "feriados_nacionais.csv"
)

FERIADOS_FIXOS: tuple[tuple[int, int, str], ...] = (
    (1, 1, "Confraternização Universal"),
    (4, 21, "Tiradentes"),
    (5, 1, "Dia do Trabalho"),
    (9, 7, "Independência do Brasil"),
    (10, 12, "Nossa Senhora Aparecida"),
    (11, 2, "Finados"),
    (11, 15, "Proclamação da República"),
    (11, 20, "Dia Nacional de Zumbi e da Consciência Negra"),
    (12, 25, "Natal"),
)


def pascoa(ano: int) -> date:
    """Domingo de Páscoa (calendário gregoriano)."""
    a = ano % 19
    b, c = divmod(ano, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    mes, dia = divmod(h + l - 7 * m + 114, 31)
    return date(ano, mes, dia + 1)


def feriados_do_ano(ano: int) -> list[tuple[date, str]]:
    domingo = pascoa(ano)
    moveis = [
        (domingo - timedelta(days=48), "Carnaval"),
        (domingo - timedelta(days=47), "Carnaval"),
        (domingo - timedelta(days=2), "Sexta-feira Santa"),
        (domingo + timedelta(days=60), "Corpus Christi"),
    ]
    fixos = [(date(ano, mes, dia), nome) for mes, dia, nome in FERIADOS_FIXOS]
    return sorted(fixos + moveis)


def gerar(ano_inicial: int = ANO_INICIAL, ano_final: int = ANO_FINAL) -> list[tuple[date, str]]:
    return [par for ano in range(ano_inicial, ano_final + 1) for par in feriados_do_ano(ano)]


def main() -> None:
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    with DESTINO.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo, lineterminator="\n")
        escritor.writerow(["data", "nome_feriado"])
        for dia, nome in gerar():
            escritor.writerow([dia.isoformat(), nome])
    print(f"Gerado: {DESTINO}")


if __name__ == "__main__":
    main()
