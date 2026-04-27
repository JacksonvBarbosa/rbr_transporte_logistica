from __future__ import annotations

from io import BytesIO

import pandas as pd
import pdfplumber

from rbr_transporte_logistica.services.partner_service import PartnerService

REQUIRED_UPLOAD_COLUMNS = [
    "km_de",
    "km_ate",
    "valor_fixo",
    "valor_km_excedente",
    "prazo_dias",
]

UPLOAD_COLUMN_ALIASES = {
    "km de": "km_de",
    "km_de": "km_de",
    "km inicial": "km_de",
    "km ate": "km_ate",
    "km_ate": "km_ate",
    "km final": "km_ate",
    "valor fixo": "valor_fixo",
    "valor_fixo": "valor_fixo",
    "preco fixo": "valor_fixo",
    "valor km excedente": "valor_km_excedente",
    "valor_km_excedente": "valor_km_excedente",
    "preco km excedente": "valor_km_excedente",
    "prazo": "prazo_dias",
    "prazo_dias": "prazo_dias",
    "prazo dias": "prazo_dias",
}


def normalize_upload_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized.columns = [
        UPLOAD_COLUMN_ALIASES.get(str(column).strip().lower(), str(column).strip().lower())
        for column in normalized.columns
    ]
    return normalized


class IngestaoService:
    def __init__(self, partner_service: PartnerService) -> None:
        self.partner_service = partner_service

    def preview_csv(self, content: bytes, separator: str = ";") -> pd.DataFrame:
        return normalize_upload_dataframe(pd.read_csv(BytesIO(content), sep=separator))

    def preview_xlsx(self, content: bytes) -> pd.DataFrame:
        return normalize_upload_dataframe(pd.read_excel(BytesIO(content)))

    def preview_pdf(self, content: bytes) -> pd.DataFrame:
        extracted_rows: list[list[str]] = []
        with pdfplumber.open(BytesIO(content)) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables() or []:
                    extracted_rows.extend([row for row in table if row])
        if not extracted_rows:
            raise ValueError("Nenhum dado tabular foi encontrado no PDF fornecido.")
        header, *rows = extracted_rows
        return normalize_upload_dataframe(pd.DataFrame(rows, columns=header))

    def importar_csv(self, *, partner_id: int, content: bytes, separator: str = ";") -> int:
        return self._importar_dataframe(partner_id=partner_id, df=self.preview_csv(content, separator))

    def importar_xlsx(self, *, partner_id: int, content: bytes) -> int:
        return self._importar_dataframe(partner_id=partner_id, df=self.preview_xlsx(content))

    def importar_pdf(self, *, partner_id: int, content: bytes) -> int:
        return self._importar_dataframe(partner_id=partner_id, df=self.preview_pdf(content))

    def _importar_dataframe(self, *, partner_id: int, df: pd.DataFrame) -> int:
        required = set(REQUIRED_UPLOAD_COLUMNS)
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Colunas obrigatorias ausentes: {', '.join(sorted(missing))}")

        prepared = df[REQUIRED_UPLOAD_COLUMNS].copy().dropna()
        for _, row in prepared.iterrows():
            self.partner_service.add_rule(
                partner_id=partner_id,
                rule_type="LINEAR",
                base_price=float(row["valor_fixo"]),
                price_per_km=float(row["valor_km_excedente"]),
                max_km=float(row["km_ate"]),
                deadline_days=int(row["prazo_dias"]),
            )
        return int(len(prepared))
