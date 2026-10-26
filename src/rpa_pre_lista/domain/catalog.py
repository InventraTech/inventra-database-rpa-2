import re
import unicodedata
from dataclasses import dataclass

from .models import RejectReason, ResolvedItem, SourceItem


def only_digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def normalize_name(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip().casefold()


@dataclass(frozen=True)
class Catalog:
    """Fornecedores, produtos e cozinhas do Inventra; traduz o 1º ano para os ids do destino."""

    suppliers: dict[str, int]
    products: dict[str, tuple[int, ...]]
    product_suppliers: frozenset[tuple[int, int]]
    kitchens: frozenset[int]

    def has_kitchen(self, id_kitchen: int | None) -> bool:
        return id_kitchen in self.kitchens

    def resolve(self, item: SourceItem) -> ResolvedItem | RejectReason:
        id_supplier = self.suppliers.get(only_digits(item.supplier_cnpj))
        if id_supplier is None:
            return RejectReason.SUPPLIER_NOT_FOUND

        candidates = self.products.get(normalize_name(item.product_name), ())
        if len(candidates) > 1:
            linked = tuple(p for p in candidates if (p, id_supplier) in self.product_suppliers)
            candidates = linked or candidates
        if not candidates:
            return RejectReason.PRODUCT_NOT_FOUND
        if len(candidates) > 1:
            return RejectReason.PRODUCT_AMBIGUOUS

        return ResolvedItem(candidates[0], id_supplier, item.quantity)
