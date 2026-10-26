from collections.abc import Iterator
from datetime import date
from itertools import groupby

import psycopg

from ..domain.models import PreLista, SourceItem

_QUERY = """
SELECT p.id_pre_lista, p.dt_lista, p.id_kitchen, i.id_item_lista,
       f.cnpj, f.nome_juridico, pr.nome, i.qtd
FROM pre_lista p
JOIN item_pre_lista i ON i.fk_pre_lista = p.id_pre_lista
JOIN fornecedor f ON f.id_fornecedor = i.fk_fornecedor
JOIN produto pr ON pr.id_produto = i.fk_produto
WHERE (%(since)s::date IS NULL OR p.dt_lista >= %(since)s::date)
  AND NOT (p.id_pre_lista = ANY(%(skip)s::int[]))
ORDER BY p.id_pre_lista, i.id_item_lista
"""


class PostgresPreListaSource:
    """Lê pre_lista e item_pre_lista do banco do 1º ano, em streaming."""

    def __init__(self, conn: psycopg.Connection, fetch_size: int) -> None:
        self._conn = conn
        self._fetch_size = fetch_size

    def fetch(self, *, since: date | None, skip: set[int]) -> Iterator[PreLista]:
        with self._conn.cursor(name="pre_lista_stream") as cur:
            cur.itersize = self._fetch_size
            cur.execute(_QUERY, {"since": since, "skip": sorted(skip)})
            for (id_pre_lista, dt_lista, id_kitchen), rows in groupby(cur, key=lambda r: r[:3]):
                items = [
                    SourceItem(
                        id_item_lista=r[3],
                        supplier_cnpj=r[4],
                        supplier_name=r[5],
                        product_name=r[6],
                        quantity=r[7],
                    )
                    for r in rows
                ]
                yield PreLista(id_pre_lista, dt_lista, items, id_kitchen)
