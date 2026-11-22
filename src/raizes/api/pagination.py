"""Paginação padrão: `?page=1&limit=10` (máximo 100) e resposta `{items, page, limit, total}`."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query
from pydantic import BaseModel


@dataclass(frozen=True, slots=True)
class PageParams:
    page: int
    limit: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


def get_page_params(
    page: Annotated[int, Query(ge=1, description="Página (começa em 1)")] = 1,
    limit: Annotated[int, Query(ge=1, le=100, description="Itens por página (máx. 100)")] = 10,
) -> PageParams:
    return PageParams(page=page, limit=limit)


PageQuery = Annotated[PageParams, Depends(get_page_params)]


class Page[T](BaseModel):
    """Resposta paginada genérica."""

    items: list[T]
    page: int
    limit: int
    total: int
