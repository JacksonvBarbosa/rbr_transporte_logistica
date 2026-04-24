from __future__ import annotations

import pandas as pd
import streamlit as st

from rbr_transporte_logistica.app.dependencies import build_freight_controller, build_partner_controller
from rbr_transporte_logistica.core.database import db_session
from rbr_transporte_logistica.services.route_builder import default_segment_pickup_modes


def render() -> None:
    st.header("Simulacao de Frete")
    st.caption("Compare parceiros e gere uma rota multi-trecho automaticamente com override manual opcional.")

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
                    st.session_state["selected_partner_ids"] = result.get("valid_partner_ids", [])
                    if result.get("suggested_route"):
                        st.session_state["last_route"] = result["suggested_route"]
                        st.session_state["selected_partner_ids"] = result["suggested_route"]["selected_partner_ids"]
                        st.session_state["selected_segment_pickup_modes"] = result["suggested_route"][
                            "segment_pickup_modes"
                        ]
                except ValueError as exc:
                    st.error(str(exc))
                    return

    simulation = st.session_state.get("last_simulation")
    if not simulation:
        st.info("Informe origem e destino para calcular a distancia automaticamente.")
        return

    st.metric("Distancia direta", f"{simulation['distance_km']:,.2f} km")
    if not simulation["results"] and not simulation.get("suggested_route"):
        st.warning("Nenhuma rota valida foi encontrada para esse trajeto.")
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
    if not comparison_df.empty:
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum parceiro consegue finalizar a rota sozinho, mas a malha valida foi analisada.")

    best_price = simulation["best_price"]
    best_deadline = simulation["best_deadline"]
    if best_price and best_deadline:
        metric_col1, metric_col2 = st.columns(2)
        metric_col1.metric("Melhor preco", f"R$ {best_price.price:,.2f}", best_price.partner_name)
        metric_col2.metric(
            "Melhor prazo", f"{best_deadline.deadline_days} dias", best_deadline.partner_name
        )

    valid_partner_ids = simulation.get("valid_partner_ids", [])
    if valid_partner_ids:
        st.caption(f"Parceiros validos para a rota atual: {len(valid_partner_ids)}")

    route = st.session_state.get("last_route")
    if route:
        summary_cols = st.columns(3)
        summary_cols[0].metric("Distancia total da rota", f"{route['total_distance_km']:,.2f} km")
        summary_cols[1].metric("Custo total da rota", f"R$ {route['total_cost']:,.2f}")
        summary_cols[2].metric("Prazo total", f"{route['total_deadline_days']} dias")
        route_points_labels = " -> ".join(
            f"{point.label} ({point.city}/{point.state})" for point in route["route_points"]
        )
        st.write(f"Rota gerada: {route_points_labels}")
        st.caption(
            "Modo atual: "
            + ("override manual" if route.get("manual_override") else "geracao automatica")
        )

        st.subheader("Trechos calculados")
        segments_df = pd.DataFrame(
            [
                {
                    "ordem": index,
                    "partner": segment.partner_name,
                    "origem": route["route_points"][0].label if index == 1 else route["route_points"][index].label,
                    "destino": route["route_points"][index + 1].label,
                    "distance_km": segment.distance_km,
                    "price": segment.segment_cost,
                    "segment_days": segment.segment_days,
                    "pickup_mode": segment.pickup_mode,
                    "total_cost": round(
                        sum(item.segment_cost for item in route["route_segments"][:index]),
                        2,
                    ),
                    "total_days": sum(item.segment_days for item in route["route_segments"][:index]),
                    "rule_type": segment.rule_type,
                }
                for index, segment in enumerate(route["route_segments"], start=1)
            ]
        )
        st.dataframe(segments_df, use_container_width=True, hide_index=True)

    st.subheader("Override manual opcional")
    use_manual_override = st.checkbox(
        "Selecionar parceiros manualmente",
        key="use_manual_route_override",
        value=False,
    )
    if use_manual_override:
        valid_partner_lookup = {
            partner.id: partner
            for partner in active_partners
            if partner.id in valid_partner_ids
        }
        partner_labels = {
            partner.id: f"{partner.name} ({partner.city}/{partner.state})"
            for partner in valid_partner_lookup.values()
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
        default_pickup_modes = default_segment_pickup_modes(len(selected_partner_ids))
        stored_pickup_modes = st.session_state.get("selected_segment_pickup_modes", [])
        if len(stored_pickup_modes) != len(selected_partner_ids):
            stored_pickup_modes = default_pickup_modes
        selected_segment_pickup_modes: list[str] = []
        if selected_partner_ids:
            st.caption("Defina o pickup mode por trecho.")
        for index, partner_id in enumerate(selected_partner_ids):
            mode = st.selectbox(
                f"{partner_labels[partner_id]}",
                options=["HUB", "DIRECT"],
                index=["HUB", "DIRECT"].index(stored_pickup_modes[index]),
                key=f"pickup_mode_segment_{index}_{partner_id}",
            )
            selected_segment_pickup_modes.append(mode)
        st.session_state["selected_segment_pickup_modes"] = selected_segment_pickup_modes

        if st.button("Aplicar override manual", key="apply_manual_route_override"):
            try:
                route = freight_controller.simulate_multi_leg(
                    origin_city=simulation["origin"].city,
                    origin_state=simulation["origin"].state,
                    destination_city=simulation["destination"].city,
                    destination_state=simulation["destination"].state,
                    partner_ids=selected_partner_ids,
                    segment_pickup_modes=selected_segment_pickup_modes,
                )
                st.session_state["last_route"] = route
                st.session_state["selected_partner_ids"] = route["selected_partner_ids"]
                st.session_state["selected_segment_pickup_modes"] = route["segment_pickup_modes"]
                st.success("Rota manual calculada com sucesso.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    else:
        if st.button("Recalcular rota automatica", key="rebuild_auto_route"):
            try:
                route = freight_controller.simulate_multi_leg(
                    origin_city=simulation["origin"].city,
                    origin_state=simulation["origin"].state,
                    destination_city=simulation["destination"].city,
                    destination_state=simulation["destination"].state,
                )
                st.session_state["last_route"] = route
                st.session_state["selected_partner_ids"] = route["selected_partner_ids"]
                st.session_state["selected_segment_pickup_modes"] = route["segment_pickup_modes"]
                st.success("Rota automatica recalculada com sucesso.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
