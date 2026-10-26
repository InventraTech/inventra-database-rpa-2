from collections.abc import Iterator
from datetime import date
from typing import Protocol

from ..domain.catalog import Catalog
from ..domain.models import PreLista, ResolvedItem


class PreListaSource(Protocol):
    """De onde vêm as pré-listas (banco do 1º ano)."""

    def fetch(self, *, since: date | None, skip: set[int]) -> Iterator[PreLista]: ...


class PreListTarget(Protocol):
    """Para onde vão as pré-listas (banco do Inventra)."""

    def load_catalog(self) -> Catalog: ...

    def imported_ids(self) -> set[int]: ...

    def save(self, pre_lista: PreLista, items: list[ResolvedItem]) -> int:
        """Grava a pré-lista e seus itens numa transação. Levanta TargetWriteError se falhar."""
        ...
