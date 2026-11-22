"""Porta da unidade de trabalho: um caso de uso = uma transação."""

from typing import Protocol


class UnitOfWork(Protocol):
    def commit(self) -> None: ...

    def rollback(self) -> None: ...
