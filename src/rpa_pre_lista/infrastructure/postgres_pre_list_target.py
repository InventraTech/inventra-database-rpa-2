from collections.abc import Iterator
from contextlib import contextmanager

import psycopg

from ..domain.catalog import Catalog, normalize_name, only_digits
from ..domain.models import PreLista, ResolvedItem
from ..errors import AlreadyRunningError, TargetWriteError

# Impede duas execuções simultâneas contra o mesmo destino.
_LOCK_KEY = 727_001


class PostgresPreListTarget:
    """Grava as pré-listas no banco do Inventra (tb_pre_list e tb_pre_list_item).

    O id da pré-lista no 1º ano fica em tb_pre_list.id_source (único): é o que torna a carga
    idempotente. A cozinha vem de pre_lista.id_kitchen, coluna que o 1º ano acrescentou ao banco.
    A conexão deve estar em autocommit: cada `save` abre a própria transação.
    """

    def __init__(self, conn: psycopg.Connection, *, dry_run: bool) -> None:
        self._conn = conn
        self._dry_run = dry_run

    @contextmanager
    def exclusive_lock(self) -> Iterator[None]:
        acquired = self._conn.execute("SELECT pg_try_advisory_lock(%s)", (_LOCK_KEY,)).fetchone()[0]
        if not acquired:
            raise AlreadyRunningError("Outra execução do RPA já está em andamento no destino.")
        try:
            yield
        finally:
            self._conn.execute("SELECT pg_advisory_unlock(%s)", (_LOCK_KEY,))

    def load_catalog(self) -> Catalog:
        suppliers = {
            only_digits(cnpj): id_supplier
            for id_supplier, cnpj in self._conn.execute("SELECT id_supplier, cnpj FROM tb_supplier")
        }

        products: dict[str, list[int]] = {}
        rows = self._conn.execute("SELECT id_product, name FROM tb_product WHERE active")
        for id_product, name in rows:
            products.setdefault(normalize_name(name), []).append(id_product)

        links = frozenset(
            self._conn.execute("SELECT id_product, id_supplier FROM tb_product_supplier").fetchall()
        )
        kitchens = frozenset(r[0] for r in self._conn.execute("SELECT id_kitchen FROM tb_kitchen"))
        return Catalog(suppliers, {k: tuple(v) for k, v in products.items()}, links, kitchens)

    def imported_ids(self) -> set[int]:
        rows = self._conn.execute("SELECT id_source FROM tb_pre_list WHERE id_source IS NOT NULL")
        return {r[0] for r in rows}

    def save(self, pre_lista: PreLista, items: list[ResolvedItem]) -> int:
        try:
            with self._conn.transaction(force_rollback=self._dry_run), self._conn.cursor() as cur:
                id_pre_list = cur.execute(
                    "INSERT INTO tb_pre_list (list_date, id_source, id_kitchen) "
                    "VALUES (%s, %s, %s) "
                    "RETURNING id_pre_list",
                    (pre_lista.dt_lista, pre_lista.id_pre_lista, pre_lista.id_kitchen),
                ).fetchone()[0]
                cur.executemany(
                    "INSERT INTO tb_pre_list_item "
                    "(id_pre_list, id_supplier, id_product, quantity) VALUES (%s, %s, %s, %s)",
                    [(id_pre_list, i.id_supplier, i.id_product, i.quantity) for i in items],
                )
        except (psycopg.IntegrityError, psycopg.DataError) as exc:
            raise TargetWriteError(str(exc)) from exc
        return id_pre_list
