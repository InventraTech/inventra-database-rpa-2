import pytest

from rpa_pre_lista.domain.catalog import Catalog, normalize_name, only_digits
from rpa_pre_lista.domain.models import RejectReason, ResolvedItem, SourceItem


def item(cnpj="12.345.678/0001-90", product="Arroz Branco", qty=5):
    return SourceItem(1, cnpj, "Fornecedor X", product, qty)


@pytest.fixture
def catalog():
    return Catalog(
        suppliers={"12345678000190": 10, "99999999000199": 20},
        products={
            "arroz branco": (100,),
            "feijao": (200, 201),
            "oleo": (300, 301),
        },
        product_suppliers=frozenset({(200, 10), (300, 10), (301, 20)}),
        kitchens=frozenset({1}),
    )


def test_only_digits():
    assert only_digits("12.345.678/0001-90") == "12345678000190"
    assert only_digits(None) == ""


def test_normalize_name_ignores_case_accents_and_spaces():
    assert normalize_name("  Feijão   PRETO ") == "feijao preto"


def test_resolves_by_cnpj_and_normalized_name(catalog):
    assert catalog.resolve(item(product="  ARROZ  branco ")) == ResolvedItem(100, 10, 5)


def test_has_kitchen(catalog):
    assert catalog.has_kitchen(1)
    assert not catalog.has_kitchen(2)
    assert not catalog.has_kitchen(None)


def test_unknown_supplier_is_rejected(catalog):
    assert catalog.resolve(item(cnpj="00.000.000/0000-00")) is RejectReason.SUPPLIER_NOT_FOUND


def test_unknown_product_is_rejected(catalog):
    assert catalog.resolve(item(product="Sal")) is RejectReason.PRODUCT_NOT_FOUND


def test_ambiguous_name_is_disambiguated_by_supplier_link(catalog):
    assert catalog.resolve(item(product="Óleo")) == ResolvedItem(300, 10, 5)


def test_ambiguous_name_without_supplier_link_is_rejected(catalog):
    result = catalog.resolve(item(product="Feijão", cnpj="99.999.999/0001-99"))
    assert result is RejectReason.PRODUCT_AMBIGUOUS
