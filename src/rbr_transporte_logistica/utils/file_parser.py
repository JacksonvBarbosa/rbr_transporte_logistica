from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO

import pandas as pd
import pdfplumber


REQUIRED_COLUMNS = {"partner", "city", "state", "price", "km"}
ORDERED_REQUIRED_COLUMNS = ["partner", "city", "state", "price", "km"]
COLUMN_ALIASES = {
    "parceiro": "partner",
    "partner": "partner",
    "cidade": "city",
    "city": "city",
    "estado": "state",
    "uf": "state",
    "state": "state",
    "preco": "price",
    "valor": "price",
    "price": "price",
    "km": "km",
    "distancia": "km",
}


@dataclass(slots=True)
class ParsedFileRow:
    partner: str
    city: str
    state: str
    price: float
    km: float


def parse_uploaded_file(filename: str, file_obj: BinaryIO) -> list[ParsedFileRow]:
    extension = filename.lower().split(".")[-1]
    if extension == "csv":
        df = pd.read_csv(file_obj)
    elif extension in {"xlsx", "xls"}:
        df = pd.read_excel(file_obj)
    elif extension == "pdf":
        df = _parse_pdf(file_obj)
    else:
        raise ValueError("Formato de arquivo sem suporte. Use CSV, XLSX ou PDF.")

    normalized = _normalize_dataframe(df)
    return [
        ParsedFileRow(
            partner=str(row["partner"]).strip(),
            city=str(row["city"]).strip(),
            state=str(row["state"]).strip().upper()[:2],
            price=float(row["price"]),
            km=float(row["km"]),
        )
        for _, row in normalized.iterrows()
    ]


def _parse_pdf(file_obj: BinaryIO) -> pd.DataFrame:
    extracted_rows: list[list[str]] = []
    content = file_obj.read()
    with pdfplumber.open(BytesIO(content)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables or []:
                extracted_rows.extend([row for row in table if row])

    if not extracted_rows:
        raise ValueError("Nenhum dado tabular foi encontrado no PDF fornecido.")

    header, *rows = extracted_rows
    return pd.DataFrame(rows, columns=header)


def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned.columns = [
        COLUMN_ALIASES.get(str(column).strip().lower(), str(column).strip().lower())
        for column in cleaned.columns
    ]
    missing = REQUIRED_COLUMNS - set(cleaned.columns)
    if missing:
        raise ValueError(f"Colunas obrigátorias ausentes: {', '.join(sorted(missing))}")

    cleaned = cleaned[ORDERED_REQUIRED_COLUMNS].dropna()
    cleaned["price"] = pd.to_numeric(cleaned["price"], errors="coerce")
    cleaned["km"] = pd.to_numeric(cleaned["km"], errors="coerce")
    cleaned = cleaned.dropna(subset=["price", "km"])
    return cleaned
