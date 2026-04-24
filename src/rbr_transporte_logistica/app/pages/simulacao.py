from __future__ import annotations

import pandas as pd
import streamlit as st

from rbr_transporte_logistica.app.dependencies import build_freight_controller, build_partner_controller
from rbr_transporte_logistica.core.database import db_session


def render() -> None:
    st.header("Simulacao de Frete")
    st.caption("Compare parceiros automaticamente e monte uma rota multi-trecho com selecao ordenada.")

    with db_session() as session:
        freight_controller = build_freight_controller(session)
        partner_controller = build_partner_controller(session)
        active_partners = partner_controller.list_partners(active_only=True)

        with st.form("simulation_form"):
            origin_col, origin_state_col = st.columns(2)
            origin_city = origin_col.text_input("Cidade de origem", value="Sao Paulo")
            origin_state = origin_state_col.text_input("UF de origem", value="SP", max_chars=2)
            dest_col, dest_state_col = st.columns(2)
            destination_city = dest_col.text_input("Cidade de destino", value="Rio de Janeiro")
            destination_state = dest_state_col.text_input("UF de destino", value="RJ", max_chars=2)
            compare = st.form_submit_button("Calcular melhor frete", type="primary")

            if compare:
                try:
                    result = freight_controller.simulate(
                        origin_city=origin_city,
                        origin_state=origin_state,
                        destination_city=destination_city,
                        destination_state=destination_state,
                    )
                    st.session_state["last_simulation"] = result
                    st.session_state.pop("last_route", None)
                    st.session_state.pop("last_quote", None)
                    default_partner_ids = (
                        [result["best_price"].partner_id] if result.get("best_price") else []
                    )
                    st.session_state["selected_partner_ids"] = default_partner_ids
                except ValueError as exc:
                    st.error(str(exc))
                    return

    simulation = st.session_state.get("last_simulation")
    if not simulation:
        st.info("Informe origem e destino para calcular a distancia automaticamente.")
        return

    st.metric("Distancia direta", f"{simulation['distance_km']:,.2f} km")
    if not simulation["results"]:
        st.warning("Nenhum parceiro ativo possui regra para essa rota.")
        return

    comparison_df = pd.DataFrame(
        [
            {
                "partner_id": row.partner_id,
                "partner_name": row.partner_name,
                "cidade": row.city,
                "uf": row.state,
                "distance_km": row.distance_km,
                "price": row.price,
                "deadline_days": row.deadline_days,
                "rule_type": row.rule_type,
            }
            for row in simulation["results"]
        ]
    )
    st.subheader("Comparativo de parceiros")
    st.dataframe(comparison_df, use_container_width=True, hide_index=True)

    best_price = simulation["best_price"]
    best_deadline = simulation["best_deadline"]
    metric_col1, metric_col2 = st.columns(2)
    metric_col1.metric("Melhor preco", f"R$ {best_price.price:,.2f}", best_price.partner_name)
    metric_col2.metric(
        "Melhor prazo", f"{best_deadline.deadline_days} dias", best_deadline.partner_name
    )

    partner_labels = {
        partner.id: f"{partner.name} ({partner.city}/{partner.state})" for partner in active_partners
    }
    valid_partner_ids = list(partner_labels.keys())
    sanitized_default = [
        partner_id
        for partner_id in st.session_state.get("selected_partner_ids", [])
        if partner_id in valid_partner_ids
    ]
    st.session_state["selected_partner_ids"] = sanitized_default
    selected_partner_ids = st.multiselect(
        "Parceiros da rota, em ordem",
        options=valid_partner_ids,
        default=sanitized_default,
        format_func=lambda partner_id: partner_labels[partner_id],
    )
    st.session_state["selected_partner_ids"] = selected_partner_ids

    if st.button("Montar rota multi-trecho"):
        try:
            route = freight_controller.simulate_multi_leg(
                origin_city=simulation["origin"].city,
                origin_state=simulation["origin"].state,
                destination_city=simulation["destination"].city,
                destination_state=simulation["destination"].state,
                partner_ids=selected_partner_ids,
            )
            st.session_state["last_route"] = route
            st.success("Rota multi-trecho calculada com sucesso.")
        except ValueError as exc:
            st.error(str(exc))

    route = st.session_state.get("last_route")
    if route:
        st.subheader("Trechos calculados")
        segments_df = pd.DataFrame(
            [
                {
                    "ordem": segment.segment_order,
                    "partner": segment.partner_name,
                    "origem": segment.origin_label,
                    "destino": segment.destination_label,
                    "distance_km": segment.distance_km,
                    "price": segment.price,
                    "deadline_days": segment.deadline_days,
                    "rule_type": segment.rule_type,
                }
                for segment in route["segments"]
            ]
        )
        st.dataframe(segments_df, use_container_width=True, hide_index=True)
