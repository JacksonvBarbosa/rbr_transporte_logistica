from __future__ import annotations

import base64
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import streamlit as st

from rbr_transporte_logistica.app.theme import apply_theme, sidebar_nav
from rbr_transporte_logistica.core.database import db_session
from rbr_transporte_logistica.repositories.quote_repository import CotacaoRepo
from rbr_transporte_logistica.utils.export_excel import build_quote_excel
from rbr_transporte_logistica.utils.export_pdf import build_quote_pdf


def gerar_proposta_pdf(cotacao, tmp_path: Path) -> Path:
    quote_data = _cotacao_to_quote_data(cotacao)
    pdf_path = tmp_path / f"{getattr(cotacao, 'number', 'cotacao')}.pdf"
    pdf_path.write_bytes(build_quote_pdf(quote_data["summary"], quote_data["items"]))
    return pdf_path


def gerar_relatorio_excel(cotacao, tmp_path: Path) -> Path:
    quote_data = _cotacao_to_quote_data(cotacao)
    excel_path = tmp_path / f"{getattr(cotacao, 'number', 'cotacao')}.xlsx"
    excel_path.write_bytes(build_quote_excel(quote_data["summary"], quote_data["items"]))
    return excel_path


def render() -> None:
    apply_theme()
    sidebar_nav("Orçamentos")
    st.markdown("### Orcamentos")

    with db_session() as session:
        repo = CotacaoRepo(session)
        quotes = repo.listar_fechadas()

    if not quotes:
        st.info("Nenhuma cotacao fechada disponivel.")
        return

    options = {
        f"{quote.number} - {quote.customer_name} - {quote.created_at:%d/%m/%Y}": quote
        for quote in quotes
    }
    tabs = st.tabs(["Orcamentos", "Documentos Internos"])

    with tabs[0]:
        selected_label = st.selectbox("Cotacao", list(options.keys()), key="quote_pdf_select")
        cotacao = options[selected_label]
        st.markdown("#### Preview da proposta")
        st.write(f"Numero: {cotacao.number}")
        st.write(f"Cliente: {cotacao.customer_name}")
        st.write(f"Data: {cotacao.created_at:%d/%m/%Y}")
        segments_df = pd.DataFrame(
            [
                {
                    "Parceiro": item.partner_name,
                    "KM": float(item.distance_km),
                    "Valor": float(item.value),
                    "Prazo": item.deadline_days,
                }
                for item in cotacao.items
            ]
        )
        st.dataframe(segments_df, use_container_width=True, hide_index=True)
        st.metric("Total", f"R$ {float(cotacao.total_value):,.2f}")
        st.metric("Prazo total", f"{cotacao.total_deadline_days} dias")
        tmp_dir = Path(".tmp_exports")
        tmp_dir.mkdir(exist_ok=True)
        pdf_path = gerar_proposta_pdf(cotacao, tmp_dir)
        st.download_button(
            "Gerar e baixar PDF",
            data=pdf_path.read_bytes(),
            file_name=pdf_path.name,
            mime="application/pdf",
        )
        if st.button("Visualizar proposta", key=f"preview_pdf_{cotacao.id}"):
            encoded = base64.b64encode(pdf_path.read_bytes()).decode("utf-8")
            st.markdown(
                f'<iframe src="data:application/pdf;base64,{encoded}" width="100%" height="640"></iframe>',
                unsafe_allow_html=True,
            )

    with tabs[1]:
        selected_label = st.selectbox("Cotacao", list(options.keys()), key="quote_excel_select")
        cotacao = options[selected_label]
        detailed_df = pd.DataFrame(
            [
                {
                    "numero": cotacao.number,
                    "cliente": cotacao.customer_name,
                    "parceiro": item.partner_name,
                    "origem": item.origin_label,
                    "destino": item.destination_label,
                    "km": float(item.distance_km),
                    "valor": float(item.value),
                    "prazo": item.deadline_days,
                    "regra": item.rule_type,
                    "pickup_mode": item.pickup_mode,
                    "icms_rate": float(cotacao.icms_rate),
                    "iss_rate": float(cotacao.iss_rate),
                    "margin_rate": float(cotacao.margin_rate),
                    "total": float(cotacao.total_value),
                }
                for item in cotacao.items
            ]
        )
        st.dataframe(detailed_df, use_container_width=True, hide_index=True)
        tmp_dir = Path(".tmp_exports")
        tmp_dir.mkdir(exist_ok=True)
        excel_path = gerar_relatorio_excel(cotacao, tmp_dir)
        st.download_button(
            "Gerar e baixar Excel",
            data=excel_path.read_bytes(),
            file_name=excel_path.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        history_df = pd.DataFrame(
            [
                {
                    "numero": quote.number,
                    "cliente": quote.customer_name,
                    "rota": quote.route_label,
                    "status": quote.status,
                    "total": float(quote.total_value),
                    "prazo_total": quote.total_deadline_days,
                    "criado_em": quote.created_at,
                }
                for quote in quotes
            ]
        )
        st.dataframe(history_df, use_container_width=True, hide_index=True)
        st.download_button(
            "Baixar historico CSV",
            data=history_df.to_csv(index=False).encode("utf-8"),
            file_name="historico_cotacoes.csv",
            mime="text/csv",
        )


def _cotacao_to_quote_data(cotacao) -> dict:
    summary = {
        "origin": cotacao.origin,
        "destination": cotacao.destination,
        "direct_distance_km": float(cotacao.direct_distance_km),
        "route_distance_km": float(cotacao.route_distance_km),
        "subtotal": float(cotacao.freight_gross),
        "taxes": float(cotacao.icms_value) + float(cotacao.iss_value),
        "margin": float(cotacao.margin_value),
        "additional_fees": 0.0,
        "total": float(cotacao.total_value),
        "total_deadline_days": int(cotacao.total_deadline_days),
    }
    items = [
        SimpleNamespace(
            origin_label=item.origin_label,
            destination_label=item.destination_label,
            partner_name=item.partner_name,
            distance_km=float(item.distance_km),
            price=float(item.value),
            deadline_days=item.deadline_days,
            rule_type=item.rule_type,
        )
        for item in cotacao.items
    ]
    return {"summary": summary, "items": items}
