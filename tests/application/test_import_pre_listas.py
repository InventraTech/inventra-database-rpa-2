from datetime import date

import pytest

from rpa_pre_lista.application.import_pre_listas import ImportPreListas
from rpa_pre_lista.domain.catalog import Catalog
from rpa_pre_lista.domain.models import PreLista, RejectReason, SourceItem
from rpa_pre_lista.errors import TargetWriteError

GOOD_CNPJ = "11.111.111/0001-11"
KITCHEN = 1


def make_item(item_id, cnpj=GOOD_CNPJ, product="Arroz", qty=3):
    return SourceItem(item_id, cnpj, "Fornecedor", product, qty)


class FakeSource:
    def __init__(self, pre_listas):
        self._pre_listas = pre_listas

    def fetch(self, *, since, skip):
        for p in self._pre_listas:
            if p.id_pre_lista not in skip and (since is None or p.dt_lista >= since):
                yield p


class FakeTarget:
    def __init__(self, done=(), fail_on=()):
        self.catalog = Catalog({"11111111000111": 1}, {"arroz": (10,)}, frozenset(), frozenset({1}))
        self.done = set(done)
        self.fail_on = set(fail_on)
        self.saved = []

    def load_catalog(self):
        return self.catalog

    def imported_ids(self):
        return set(self.done)

    def save(self, pre_lista, items):
        if pre_lista.id_pre_lista in self.fail_on:
            raise TargetWriteError("violação de integridade")
        self.saved.append((pre_lista.id_pre_lista, items))
        return 100 + len(self.saved)


def good_list(id_pre_lista, day=1):
    return PreLista(id_pre_lista, date(2025, 3, day), [make_item(id_pre_lista * 10)], KITCHEN)


def mixed_list(id_pre_lista):
    items = [make_item(1), make_item(2, cnpj="00.000.000/0000-00")]
    return PreLista(id_pre_lista, date(2025, 3, 1), items, KITCHEN)


def test_imports_every_valid_list():
    target = FakeTarget()
    summary = ImportPreListas(FakeSource([good_list(1), good_list(2)]), target).execute()

    assert (summary.lists_read, summary.lists_imported, summary.items_imported) == (2, 2, 2)
    assert [s[0] for s in target.saved] == [1, 2]
    assert not summary.rejections


def test_list_with_unmatched_item_is_skipped_and_reported():
    target = FakeTarget()
    summary = ImportPreListas(FakeSource([mixed_list(1)]), target).execute()

    assert target.saved == []
    assert summary.lists_skipped == 1
    assert [r.reason for r in summary.rejections] == [RejectReason.SUPPLIER_NOT_FOUND]


def test_allow_partial_imports_only_the_valid_items():
    target = FakeTarget()
    summary = ImportPreListas(FakeSource([mixed_list(1)]), target, allow_partial=True).execute()

    (id_pre_lista, items), = target.saved
    assert (id_pre_lista, len(items)) == (1, 1)
    assert summary.lists_imported == 1 and len(summary.rejections) == 1


def test_already_imported_lists_are_not_read_again():
    target = FakeTarget(done={1})
    summary = ImportPreListas(FakeSource([good_list(1), good_list(2)]), target).execute()

    assert [s[0] for s in target.saved] == [2]
    assert summary.lists_read == 1


def test_since_filters_old_lists():
    source = FakeSource([good_list(1, day=1), good_list(2, day=20)])
    target = FakeTarget()
    ImportPreListas(source, target).execute(since=date(2025, 3, 10))

    assert [s[0] for s in target.saved] == [2]


def test_limit_stops_after_n_lists():
    target = FakeTarget()
    summary = ImportPreListas(
        FakeSource([good_list(1), good_list(2), good_list(3)]), target, limit=2
    ).execute()

    assert summary.lists_read == 2
    assert [s[0] for s in target.saved] == [1, 2]


def test_write_failure_is_counted_and_does_not_stop_the_run():
    target = FakeTarget(fail_on={1})
    summary = ImportPreListas(FakeSource([good_list(1), good_list(2)]), target).execute()

    assert summary.lists_failed == 1
    assert summary.lists_imported == 1
    assert [s[0] for s in target.saved] == [2]


@pytest.mark.parametrize("allow_partial", [False, True])
def test_list_with_no_valid_item_is_never_saved(allow_partial):
    only_bad = PreLista(
        1, date(2025, 3, 1), [make_item(1, cnpj="00.000.000/0000-00")], KITCHEN
    )
    target = FakeTarget()
    summary = ImportPreListas(FakeSource([only_bad]), target, allow_partial=allow_partial).execute()

    assert target.saved == [] and summary.lists_skipped == 1


def test_each_rejection_is_logged_with_ids_and_reason_only(caplog):
    with caplog.at_level("WARNING"):
        ImportPreListas(FakeSource([mixed_list(5)]), FakeTarget()).execute()

    line = next(m for m in caplog.messages if "rejeitado" in m)
    assert line == "Pré-lista #5, item #2 rejeitado: SUPPLIER_NOT_FOUND"
    assert "00.000.000" not in caplog.text  # nada de CNPJ no log (o repositório é público)


@pytest.mark.parametrize("id_kitchen", [None, 99])
def test_list_with_missing_or_unknown_kitchen_is_skipped_and_reported(id_kitchen):
    pre_lista = PreLista(1, date(2025, 3, 1), [make_item(1)], id_kitchen)
    target = FakeTarget()
    summary = ImportPreListas(FakeSource([pre_lista]), target, allow_partial=True).execute()

    assert target.saved == [] and summary.lists_skipped == 1
    (rejection,) = summary.rejections
    assert (rejection.id_pre_lista, rejection.item, rejection.reason) == (
        1,
        None,
        RejectReason.KITCHEN_NOT_FOUND,
    )
    # a lista inteira foi rejeitada, não um item
    assert "Itens rejeitados:       0" in summary.lines()
