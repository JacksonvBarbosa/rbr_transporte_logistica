from __future__ import annotations

from dataclasses import asdict, is_dataclass
from io import BytesIO
from typing import Iterable

import pandas as pd


def build_quote_excel(summary, items: Iterable) -> bytes:
    buffer = BytesIO()
    summary_payload = asdict(summary) if is_dataclass(summary) else dict(summary)
    items_payload = []
    for item in items:
        if is_dataclass(item):
            items_payload.append(asdict(item))
        elif hasattr(item, "__dict__"):
            items_payload.append(item.__dict__)
        else:
            items_payload.append(dict(item))

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame(items_payload).to_excel(writer, sheet_name="segment_breakdown", index=False)
        pd.DataFrame([summary_payload]).to_excel(writer, sheet_name="summary", index=False)

    buffer.seek(0)
    return buffer.read()
