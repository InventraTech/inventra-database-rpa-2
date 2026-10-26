import csv
from datetime import datetime
from pathlib import Path

from ..domain.models import Rejection


def write_rejections(directory: Path, rejections: list[Rejection]) -> Path | None:
    if not rejections:
        return None
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"rejeitados_{datetime.now():%Y%m%d_%H%M%S}.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow(
            ["id_pre_lista", "id_item_lista", "cnpj", "fornecedor", "produto", "qtd", "motivo"]
        )
        for r in rejections:
            writer.writerow(
                [
                    r.id_pre_lista,
                    r.item.id_item_lista,
                    r.item.supplier_cnpj,
                    r.item.supplier_name,
                    r.item.product_name,
                    r.item.quantity,
                    r.reason.value,
                ]
            )
    return path
