from __future__ import annotations

from dataclasses import asdict

import pandas as pd
import streamlit as st

from rbr_transporte_logistica.app.dependencies import build_quote_controller


def render() -> None:
    st.header("Orcamento")
    st.caption("Componha impostos, margem e taxas adicionais para fechar a cotacao final.")

    route = st.session_state.get("last_route")
    if not route or not route.get("segments"):
        st.info("Monte uma rota multi-trecho na simulacao antes de gerar o orcamento.")
        return

    tax_col, margin_col, fee_col = st.columns(3)
    tax_rate = tax_col.number_input("Impostos (%)", min_value=0.0, value=12.0, step=0.5) / 100
    margin_rate = margin_col.number_input("Margem (%)", min_value=0.0, value=8.0, step=0.5) / 100
    additional_fee = fee_col.number_input("Taxas adicionais", min_value=0.0, value=0.0, step=10.0)

    controller = build_quote_controller()
    quote_data = controller.create_quote(
        origin=f"{route['origin'].city}/{route['origin'].state}",
        destination=f"{route['destination'].city}/{route['destination'].state}",
        direct_distance_km=route["direct_distance_km"],
        segments=route["segments"],
        tax_rate=tax_rate,
        margin_rate=margin_rate,
        additional_fee=additional_fee,
    )
    st.session_state["last_quote"] = quote_data

    summary = quote_data["summary"]
    metric_cols = st.columns(4)
    metric_cols[0].metric("Subtotal", f"R$ {summary.subtotal:,.2f}")
    metric_cols[1].metric("Impostos", f"R$ {summary.taxes:,.2f}")
    metric_cols[2].metric("Margem", f"R$ {summary.margin:,.2f}")
    metric_cols[3].metric("Total", f"R$ {summary.total:,.2f}")

    st.write(asdict(summary))

    st.subheader("Detalhamento por trecho")
    segments_df = pd.DataFrame([asdict(segment) for segment in quote_data["items"]])
    st.dataframe(segments_df, use_container_width=True, hide_index=True)

    excel_bytes = controller.export_excel(quote_data)
    pdf_bytes = controller.export_pdf(quote_data)

    col1, col2 = st.columns(2)
    col1.download_button(
        "Baixar Excel",
        data=excel_bytes,
        file_name="orcamento_frete.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    col2.download_button(
        "Baixar PDF",
        data=pdf_bytes,
        file_name="orcamento_frete.pdf",
        mime="application/pdf",
    )
