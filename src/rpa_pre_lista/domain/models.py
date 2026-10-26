from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class RejectReason(StrEnum):
    SUPPLIER_NOT_FOUND = "SUPPLIER_NOT_FOUND"
    PRODUCT_NOT_FOUND = "PRODUCT_NOT_FOUND"
    PRODUCT_AMBIGUOUS = "PRODUCT_AMBIGUOUS"


@dataclass(frozen=True)
class SourceItem:
    id_item_lista: int
    supplier_cnpj: str
    supplier_name: str
    product_name: str
    quantity: int


@dataclass(frozen=True)
class PreLista:
    id_pre_lista: int
    dt_lista: date
    items: list[SourceItem] = field(default_factory=list)


@dataclass(frozen=True)
class ResolvedItem:
    id_product: int
    id_supplier: int
    quantity: int


@dataclass(frozen=True)
class Rejection:
    id_pre_lista: int
    item: SourceItem
    reason: RejectReason
