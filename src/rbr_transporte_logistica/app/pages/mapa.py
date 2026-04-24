from __future__ import annotations

import folium
import streamlit as st
import streamlit.components.v1 as components

from rbr_transporte_logistica.app.dependencies import build_partner_controller
from rbr_transporte_logistica.core.database import db_session
from rbr_transporte_logistica.utils.geo_utils import map_center


def render() -> None:
    st.header("Mapa de Parceiros")
    st.caption("Selecione parceiros pelo mapa e visualize os trechos da rota atual.")

    with db_session() as session:
        partner_controller = build_partner_controller(session)
        partners = [
            partner
            for partner in partner_controller.list_partners()
            if partner.latitude is not None and partner.longitude is not None
        ]

    if not partners:
        st.info("Cadastre parceiros para visualizar o mapa.")
        return

    partner_labels = {partner.id: f"{partner.name} ({partner.city}/{partner.state})" for partner in partners}
    selected_partner_ids = st.multiselect(
        "Parceiros selecionados no mapa",
        options=list(partner_labels.keys()),
        default=st.session_state.get("selected_partner_ids", []),
        format_func=lambda partner_id: partner_labels[partner_id],
    )
    st.session_state["selected_partner_ids"] = selected_partner_ids

    all_points = [(partner.latitude, partner.longitude) for partner in partners]
    route = st.session_state.get("last_route")
    if route:
        all_points.extend((point.latitude, point.longitude) for point in route["route_points"])

    map_view = folium.Map(location=map_center(all_points), zoom_start=5, control_scale=True)

    for partner in partners:
        color = "green" if partner.id in selected_partner_ids else "blue"
        folium.Marker(
            location=[partner.latitude, partner.longitude],
            popup=f"{partner.name} | {partner.city}/{partner.state}",
            tooltip=partner.name,
            icon=folium.Icon(color=color, icon="truck", prefix="fa"),
        ).add_to(map_view)

    if route:
        coordinates = [(point.latitude, point.longitude) for point in route["route_points"]]
        folium.PolyLine(coordinates, color="red", weight=4, opacity=0.85).add_to(map_view)
        for point in route["route_points"]:
            folium.CircleMarker(
                location=[point.latitude, point.longitude],
                radius=6,
                color="orange",
                fill=True,
                fill_opacity=0.8,
                popup=f"{point.label} - {point.city}/{point.state}",
            ).add_to(map_view)

    components.html(map_view._repr_html_(), height=560)
