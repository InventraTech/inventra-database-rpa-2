import logging
import time
from datetime import date

from ..domain.catalog import Catalog
from ..domain.models import PreLista, Rejection, RejectReason
from ..errors import TargetWriteError
from .ports import PreListaSource, PreListTarget
from .summary import ImportSummary

log = logging.getLogger(__name__)


class ImportPreListas:
    """Caso de uso: importa para o Inventra as pré-listas do 1º ano ainda não importadas."""

    def __init__(
        self,
        source: PreListaSource,
        target: PreListTarget,
        *,
        allow_partial: bool = False,
        limit: int | None = None,
    ) -> None:
        self._source = source
        self._target = target
        self._allow_partial = allow_partial
        self._limit = limit

    def execute(self, *, since: date | None = None) -> ImportSummary:
        started = time.monotonic()
        summary = ImportSummary()

        catalog = self._target.load_catalog()
        done = self._target.imported_ids()
        log.info(
            "Destino: %d fornecedores, %d nomes de produto, %d cozinhas, "
            "%d pré-listas já importadas",
            len(catalog.suppliers),
            len(catalog.products),
            len(catalog.kitchens),
            len(done),
        )

        for pre_lista in self._source.fetch(since=since, skip=done):
            if self._limit is not None and summary.lists_read >= self._limit:
                break
            summary.lists_read += 1
            self._import_one(catalog, pre_lista, summary)

        summary.elapsed_seconds = time.monotonic() - started
        return summary

    def _import_one(self, catalog: Catalog, pre_lista: PreLista, summary: ImportSummary) -> None:
        if not catalog.has_kitchen(pre_lista.id_kitchen):
            summary.rejections.append(
                Rejection(pre_lista.id_pre_lista, None, RejectReason.KITCHEN_NOT_FOUND)
            )
            summary.lists_skipped += 1
            log.warning(
                "Pré-lista #%d ignorada: cozinha %s não existe no Inventra",
                pre_lista.id_pre_lista,
                pre_lista.id_kitchen,
            )
            return

        resolved = []
        rejected = []
        for item in pre_lista.items:
            result = catalog.resolve(item)
            if isinstance(result, RejectReason):
                rejected.append(Rejection(pre_lista.id_pre_lista, item, result))
            else:
                resolved.append(result)
        summary.rejections.extend(rejected)
        for r in rejected:
            # só ids e motivo: o log pode ser público; os nomes e CNPJs ficam no CSV de rejeitados
            log.warning(
                "Pré-lista #%d, item #%d rejeitado: %s",
                r.id_pre_lista,
                r.item.id_item_lista,
                r.reason.value,
            )

        if not resolved or (rejected and not self._allow_partial):
            summary.lists_skipped += 1
            log.warning(
                "Pré-lista #%d ignorada: %d de %d itens sem correspondência no Inventra",
                pre_lista.id_pre_lista,
                len(rejected),
                len(pre_lista.items),
            )
            return

        try:
            id_pre_list = self._target.save(pre_lista, resolved)
        except TargetWriteError:
            summary.lists_failed += 1
            log.exception("Pré-lista #%d falhou e foi revertida", pre_lista.id_pre_lista)
            return

        summary.lists_imported += 1
        summary.items_imported += len(resolved)
        log.info(
            "Pré-lista #%d -> tb_pre_list %s (%d itens%s)",
            pre_lista.id_pre_lista,
            id_pre_list,
            len(resolved),
            f", {len(rejected)} rejeitados" if rejected else "",
        )
