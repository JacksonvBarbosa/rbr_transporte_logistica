from __future__ import annotations

from io import BytesIO

import pandas as pd
import pdfplumber
import streamlit as st

from rbr_transporte_logistica.app.dependencies import build_partner_controller
from rbr_transporte_logistica.app.theme import apply_theme, sidebar_nav
from rbr_transporte_logistica.core.database import db_session
from rbr_transporte_logistica.repositories.freight_repository import FreightRepository
from rbr_transporte_logistica.repositories.partner_repository import PartnerRepository
from rbr_transporte_logistica.repositories.quote_repository import TabelaFreteRepo
from rbr_transporte_logistica.services.ingestao_service import (
    IngestaoService,
    REQUIRED_UPLOAD_COLUMNS,
    normalize_upload_dataframe,
)
from rbr_transporte_logistica.services.partner_service import PartnerService


def preview_dataframe(
    file_name: str,
    file_bytes: bytes,
    separator: str = ";",
    service: IngestaoService | None = None,
) -> pd.DataFrame:
    extension = file_name.lower().rsplit(".", 1)[-1]
    if service is not None:
        if extension == "csv":
            return service.preview_csv(file_bytes, separator)
        if extension in {"xlsx", "xls"}:
            return service.preview_xlsx(file_bytes)
        if extension == "pdf":
            return service.preview_pdf(file_bytes)
    if extension == "csv":
        return normalize_upload_dataframe(pd.read_csv(BytesIO(file_bytes), sep=separator))
    if extension in {"xlsx", "xls"}:
        return normalize_upload_dataframe(pd.read_excel(BytesIO(file_bytes)))
    if extension == "pdf":
        extracted_rows: list[list[str]] = []
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables() or []:
                    extracted_rows.extend([row for row in table if row])
        if not extracted_rows:
            raise ValueError("Nenhum dado tabular foi encontrado no PDF fornecido.")
        header, *rows = extracted_rows
        return normalize_upload_dataframe(pd.DataFrame(rows, columns=header))
    raise ValueError("Formato de arquivo sem suporte.")


def find_missing_columns(df: pd.DataFrame) -> list[str]:
    return [column for column in REQUIRED_UPLOAD_COLUMNS if column not in df.columns]


def apply_column_mapping(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    inverse_mapping = {value: key for key, value in mapping.items() if value}
    return df.rename(columns=inverse_mapping)


def render() -> None:
    apply_theme()
    sidebar_nav("Upload de Tabelas")
    st.header("Upload de Tabelas")
    st.info(
        "📎 Use esta página para importar a planilha enviada por um parceiro durante o cadastro. "
        "O arquivo deve conter as colunas: **km_de, km_ate, valor_fixo, valor_km_excedente, prazo_dias**. "
        "Após a importação, as regras do parceiro serão atualizadas automaticamente.",
        icon="ℹ️",
    )

    with db_session() as session:
        controller = build_partner_controller(session)
        partner_service = PartnerService(PartnerRepository(session), FreightRepository(session))
        ingestao = IngestaoService(partner_service)
        tabela_repo = TabelaFreteRepo(session)
        partners = controller.list_partners()
        if not partners:
            st.info("Cadastre um parceiro antes de importar tabelas.")
            return

        partner_options = {
            f"{partner.name} ({partner.city}/{partner.state})": partner for partner in partners
        }
        selected_label = st.selectbox("Parceiro destino", list(partner_options.keys()))
        selected_partner = partner_options[selected_label]
        uploaded_file = st.file_uploader("Arquivo da tabela", type=["xlsx", "csv", "pdf"])
        st.caption("Formatos aceitos: XLSX, CSV (separador configurável) e PDF com tabela estruturada.")
        description = st.text_input("Descricao da tabela", value="")
        csv_separator = (
            st.text_input("Separador CSV", value=";")
            if uploaded_file and uploaded_file.name.lower().endswith(".csv")
            else ";"
        )

        preview_df = None
        mapped_df = None
        missing_columns: list[str] = []
        mapping: dict[str, str] = {}
        if uploaded_file:
            preview_df = preview_dataframe(
                uploaded_file.name,
                uploaded_file.getvalue(),
                csv_separator,
                ingestao,
            )
            st.markdown("#### Preview antes de importar")
            st.dataframe(preview_df.head(10), use_container_width=True, hide_index=True)
            missing_columns = find_missing_columns(preview_df)
            if missing_columns:
                st.warning(f"Colunas obrigatorias faltando: {', '.join(missing_columns)}")
                st.markdown("#### Mapeamento de colunas")
                available_columns = list(preview_df.columns)
                for required_column in REQUIRED_UPLOAD_COLUMNS:
                    mapping[required_column] = st.selectbox(
                        f"Mapear {required_column}",
                        options=[""] + available_columns,
                        index=(
                            0
                            if required_column not in available_columns
                            else available_columns.index(required_column) + 1
                        ),
                        key=f"mapping_{required_column}",
                    )
                if any(mapping.values()):
                    mapped_df = apply_column_mapping(preview_df, mapping)
                    still_missing = find_missing_columns(mapped_df)
                    if not still_missing:
                        st.success("Mapeamento pronto para importacao.")
                        st.dataframe(
                            mapped_df.head(10),
                            use_container_width=True,
                            hide_index=True,
                        )
                        preview_df = mapped_df
                        missing_columns = []
            if st.button(
                "Importar tabela",
                key="import_table_button",
                type="primary",
                disabled=preview_df is None or bool(missing_columns),
            ):
                extension = uploaded_file.name.lower().rsplit(".", 1)[-1]
                file_bytes = uploaded_file.getvalue()
                if mapped_df is not None and extension != "pdf":
                    buffer = BytesIO()
                    if extension == "csv":
                        mapped_df.to_csv(buffer, index=False, sep=csv_separator)
                    else:
                        mapped_df.to_excel(buffer, index=False)
                    file_bytes = buffer.getvalue()
                if extension == "csv":
                    total = ingestao.importar_csv(
                        partner_id=selected_partner.id,
                        content=file_bytes,
                        separator=csv_separator,
                    )
                elif extension in {"xlsx", "xls"}:
                    total = ingestao.importar_xlsx(
                        partner_id=selected_partner.id,
                        content=file_bytes,
                    )
                else:
                    total = ingestao.importar_pdf(
                        partner_id=selected_partner.id,
                        content=file_bytes,
                    )
                tabela_repo.criar_tabela(
                    partner_id=selected_partner.id,
                    description=description or uploaded_file.name,
                    filename=uploaded_file.name,
                    source_type=extension,
                    row_count=total,
                    column_mapping={key: value for key, value in mapping.items() if value},
                )
                session.commit()
                st.success(
                    f"Tabela importada: {total} faixas carregadas para {selected_partner.name}."
                )
                st.rerun()

        st.markdown("#### Historico de tabelas importadas")
        history_df = pd.DataFrame(
            [
                {
                    "id": item.id,
                    "parceiro": item.partner.name if item.partner else item.partner_id,
                    "descricao": item.description,
                    "data_importacao": item.created_at,
                    "faixas": item.row_count,
                    "status": item.status,
                }
                for item in tabela_repo.listar_tabelas()
            ]
        )
        if history_df.empty:
            st.info("Nenhuma tabela importada ainda.")
            return
        st.dataframe(
            history_df.drop(columns=["id"]),
            use_container_width=True,
            hide_index=True,
        )
        for _, row in history_df.iterrows():
            if st.button("Desativar tabela", key=f"deactivate_table_{int(row['id'])}"):
                tabela_repo.deletar_tabela(int(row["id"]))
                session.commit()
                st.success("Tabela desativada.")
                st.rerun()
