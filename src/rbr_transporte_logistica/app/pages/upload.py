from __future__ import annotations

import streamlit as st

from rbr_transporte_logistica.app.dependencies import build_freight_controller
from rbr_transporte_logistica.core.database import db_session


def render() -> None:
    st.header("Upload de Tabelas")
    st.write("Importe arquivos CSV, XLSX ou PDF com colunas de parceiro e frete.")

    uploaded_file = st.file_uploader("Selecione um arquivo", type=["csv", "xlsx", "xls", "pdf"])
    if not uploaded_file:
        return

    with db_session() as session:
        controller = build_freight_controller(session)
        try:
            result = controller.ingest_file(uploaded_file.name, uploaded_file.getvalue())
            st.success(
                f"Importacao concluida. Linhas: {result.rows_processed} | Regras: {result.rules_created}"
            )
        except ValueError as exc:
            st.error(str(exc))
