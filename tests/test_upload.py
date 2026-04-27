from __future__ import annotations

from io import BytesIO

import pandas as pd

from rbr_transporte_logistica.app.pages import upload


def test_preview_dataframe_with_expected_columns_for_csv():
    df = pd.DataFrame(
        [
            {
                "km_de": 0,
                "km_ate": 100,
                "valor_fixo": 200,
                "valor_km_excedente": 1.5,
                "prazo_dias": 2,
            }
        ]
    )
    buffer = BytesIO()
    df.to_csv(buffer, index=False, sep=";")

    preview = upload.preview_dataframe("tabela.csv", buffer.getvalue(), ";")

    assert list(preview.columns) == [
        "km_de",
        "km_ate",
        "valor_fixo",
        "valor_km_excedente",
        "prazo_dias",
    ]
    assert upload.find_missing_columns(preview) == []


def test_find_missing_columns_returns_required_warning_columns():
    df = pd.DataFrame([{"km_de": 0, "km_ate": 100, "valor_fixo": 200}])

    missing = upload.find_missing_columns(df)

    assert missing == ["valor_km_excedente", "prazo_dias"]


def test_apply_column_mapping_renames_manual_mapping_to_required_schema():
    df = pd.DataFrame(
        [
            {
                "faixa_inicio": 0,
                "faixa_fim": 100,
                "preco_base": 200,
                "preco_extra": 1.5,
                "prazo": 2,
            }
        ]
    )

    mapped = upload.apply_column_mapping(
        df,
        {
            "km_de": "faixa_inicio",
            "km_ate": "faixa_fim",
            "valor_fixo": "preco_base",
            "valor_km_excedente": "preco_extra",
            "prazo_dias": "prazo",
        },
    )

    assert upload.find_missing_columns(mapped) == []
    assert list(mapped[upload.REQUIRED_UPLOAD_COLUMNS].iloc[0]) == [0, 100, 200, 1.5, 2]
