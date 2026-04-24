from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ETLResult:
    rows_processed: int
    partners_created: int
    rules_created: int
