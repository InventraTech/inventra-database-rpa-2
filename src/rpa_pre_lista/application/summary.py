from dataclasses import dataclass, field

from ..domain.models import Rejection


@dataclass
class ImportSummary:
    lists_read: int = 0
    lists_imported: int = 0
    lists_skipped: int = 0
    lists_failed: int = 0
    items_imported: int = 0
    rejections: list[Rejection] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    def lines(self) -> list[str]:
        return [
            f"Pré-listas lidas:       {self.lists_read}",
            f"Pré-listas importadas:  {self.lists_imported}",
            f"Pré-listas ignoradas:   {self.lists_skipped}",
            f"Pré-listas com erro:    {self.lists_failed}",
            f"Itens importados:       {self.items_imported}",
            f"Itens rejeitados:       {len(self.rejections)}",
            f"Tempo:                  {self.elapsed_seconds:.2f}s",
        ]
