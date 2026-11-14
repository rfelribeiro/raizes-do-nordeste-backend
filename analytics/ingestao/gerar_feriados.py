"""Gera `seeds/feriados_nacionais.csv` (feriados nacionais do Brasil, 2024-2030).

Colunas: data_feriado, nome_feriado, tipo_feriado (sempre "nacional" por ora).

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

START_YEAR = 2024
END_YEAR = 2030
HOLIDAY_TYPE = "nacional"
TARGET = (
    Path(__file__).resolve().parents[1] / "dbt" / "raizes_dw" / "seeds" / "feriados_nacionais.csv"
)

FIXED_HOLIDAYS: tuple[tuple[int, int, str], ...] = (
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


def easter(year: int) -> date:
    """Domingo de Páscoa (calendário gregoriano)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def holidays_of_year(year: int) -> list[tuple[date, str]]:
    easter_sunday = easter(year)
    movable = [
        (easter_sunday - timedelta(days=48), "Carnaval"),
        (easter_sunday - timedelta(days=47), "Carnaval"),
        (easter_sunday - timedelta(days=2), "Sexta-feira Santa"),
        (easter_sunday + timedelta(days=60), "Corpus Christi"),
    ]
    fixed = [(date(year, month, day), name) for month, day, name in FIXED_HOLIDAYS]
    return sorted(fixed + movable)


def generate(start_year: int = START_YEAR, end_year: int = END_YEAR) -> list[tuple[date, str]]:
    return [pair for year in range(start_year, end_year + 1) for pair in holidays_of_year(year)]


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with TARGET.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(["data_feriado", "nome_feriado", "tipo_feriado"])
        for day, name in generate():
            writer.writerow([day.isoformat(), name, HOLIDAY_TYPE])
    print(f"Gerado: {TARGET}")


if __name__ == "__main__":
    main()
