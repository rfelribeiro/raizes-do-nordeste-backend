"""Verifica a regra de dependência entre camadas analisando imports com ast (stdlib)."""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
ROOT_PACKAGE = "raizes"

# camada -> prefixos de módulo proibidos
FORBIDDEN: dict[str, tuple[str, ...]] = {
    "domain": (
        "raizes.api",
        "raizes.application",
        "raizes.infrastructure",
        "fastapi",
        "pydantic",
        "sqlalchemy",
        "starlette",
    ),
    "application": ("raizes.api", "raizes.infrastructure", "fastapi", "sqlalchemy"),
    "api": ("raizes.infrastructure.db",),
}
# Arquivos autorizados a fazer a composição (podem importar infraestrutura).
COMPOSITION_FILES = {"api/dependencies.py"}


def _matches(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(prefix + ".")


def imported_modules(source: str, module_name: str, is_package: bool) -> set[str]:
    """Módulos importados em `source`, com imports relativos resolvidos para absolutos."""
    modules: set[str] = set()
    package_parts = module_name.split(".") if is_package else module_name.split(".")[:-1]
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package_parts[: len(package_parts) - (node.level - 1)]
                target = ".".join([*base, *([node.module] if node.module else [])])
            else:
                target = node.module or ""
            modules.add(target)
            # `from pkg import submodule` também pode importar um submódulo
            modules.update(f"{target}.{alias.name}" for alias in node.names)
    return modules


def violations_in(source: str, layer: str, module_name: str, relative_path: str) -> list[str]:
    if relative_path in COMPOSITION_FILES:
        return []
    found = imported_modules(source, module_name, relative_path.endswith("__init__.py"))
    return sorted(
        f"{module}" for module in found for prefix in FORBIDDEN[layer] if _matches(module, prefix)
    )


def _python_files(layer: str) -> list[Path]:
    return sorted((SRC / ROOT_PACKAGE / layer).rglob("*.py"))


@pytest.mark.parametrize("layer", sorted(FORBIDDEN))
def test_layer_respects_dependency_rule(layer: str) -> None:
    files = _python_files(layer)
    assert files, f"camada {layer} sem arquivos: o teste não verificaria nada"
    problems: list[str] = []
    for path in files:
        relative = path.relative_to(SRC / ROOT_PACKAGE).as_posix()
        module_name = ".".join(path.relative_to(SRC).with_suffix("").parts)
        problems.extend(
            f"{path.relative_to(SRC)} importa {bad}"
            for bad in violations_in(path.read_text(), layer, module_name, relative)
        )
    assert not problems, "Violações da regra de dependência:\n" + "\n".join(problems)


def test_detector_flags_forbidden_imports() -> None:
    assert violations_in("import fastapi", "domain", "raizes.domain.x", "x.py") == ["fastapi"]
    assert violations_in(
        "from raizes.infrastructure import config", "application", "raizes.application.x", "x.py"
    )
    assert violations_in(
        "from raizes.infrastructure.db import session", "api", "raizes.api.x", "x.py"
    )
    assert violations_in("from ...api import x", "domain", "raizes.domain.shared.y", "y.py")


def test_detector_allows_composition_file_and_clean_code() -> None:
    source = "from raizes.infrastructure.db.session import get_engine"
    assert violations_in(source, "api", "raizes.api.dependencies", "api/dependencies.py") == []
    assert violations_in("import json", "domain", "raizes.domain.x", "x.py") == []
