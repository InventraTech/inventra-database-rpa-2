import csv

from rpa_pre_lista.domain.models import Rejection, RejectReason, SourceItem
from rpa_pre_lista.infrastructure.rejection_report import write_rejections


def test_no_rejections_writes_nothing(tmp_path):
    assert write_rejections(tmp_path, []) is None
    assert list(tmp_path.iterdir()) == []


def test_writes_one_row_per_rejection(tmp_path):
    rejection = Rejection(
        12, SourceItem(40, "12.345.678/0001-90", "Forn", "Sal", 2), RejectReason.PRODUCT_NOT_FOUND
    )
    path = write_rejections(tmp_path, [rejection])

    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh, delimiter=";"))
    assert rows[1] == ["12", "40", "12.345.678/0001-90", "Forn", "Sal", "2", "PRODUCT_NOT_FOUND"]
