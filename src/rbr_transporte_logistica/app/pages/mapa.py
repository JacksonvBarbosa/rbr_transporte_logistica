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

    simulation = st.session_state.get("last_simulation")
    visible_partner_ids = set(simulation.get("valid_partner_ids", [])) if simulation else {partner.id for partner in partners}
    filtered_partners = [partner for partner in partners if partner.id in visible_partner_ids]
    if not filtered_partners:
        filtered_partners = partners

    partner_labels = {partner.id: f"{partner.name} ({partner.city}/{partner.state})" for partner in filtered_partners}
    valid_partner_ids = list(partner_labels.keys())
    sanitized_default = [
        partner_id
        for partner_id in st.session_state.get("selected_partner_ids", [])
        if partner_id in valid_partner_ids
    ]
    st.session_state["selected_partner_ids"] = sanitized_default
    selected_partner_ids = st.multiselect(
        "Parceiros selecionados no mapa",
        options=valid_partner_ids,
        default=sanitized_default,
        format_func=lambda partner_id: partner_labels[partner_id],
    )
    st.session_state["selected_partner_ids"] = selected_partner_ids

    all_points = [(partner.latitude, partner.longitude) for partner in filtered_partners]
    route = st.session_state.get("last_route")
    if route:
        all_points.extend((point.latitude, point.longitude) for point in route["physical_path_points"])

    map_view = folium.Map(location=map_center(all_points), zoom_start=5, control_scale=True)

    route_partner_ids = set(route.get("selected_partner_ids", [])) if route else set()
    for partner in filtered_partners:
        color = "green" if partner.id in selected_partner_ids else "blue"
        if partner.id in route_partner_ids:
            color = "red" if route.get("manual_override") else "darkgreen"
        folium.Marker(
            location=[partner.latitude, partner.longitude],
            popup=f"{partner.name} | {partner.city}/{partner.state}",
            tooltip=partner.name,
            icon=folium.Icon(color=color, icon="truck", prefix="fa"),
        ).add_to(map_view)

    if route:
        legend_added = set()
        for index, segment in enumerate(route.get("route_segments", []), start=1):
            start = route["route_points"][0] if index == 1 else route["route_points"][index]
            end = route["route_points"][index + 1]
            coordinates = [(start.latitude, start.longitude)]
            if segment.pickup_mode == "HUB":
                partner_point = route["route_points"][index]
                coordinates.append((partner_point.latitude, partner_point.longitude))
            coordinates.append((end.latitude, end.longitude))
            color = "#f59e0b" if segment.pickup_mode == "HUB" else "#2563eb"
            tooltip = (
                f"Trecho {index}: {segment.partner_name} | "
                f"{segment.pickup_mode} | "
                f"{segment.distance_km:,.2f} km | "
                f"{segment.segment_days} dias"
            )
            folium.PolyLine(
                coordinates,
                color=color,
                weight=5,
                opacity=0.9,
                tooltip=tooltip,
            ).add_to(map_view)
            if segment.pickup_mode not in legend_added:
                legend_added.add(segment.pickup_mode)
        for index, point in enumerate(route["physical_path_points"], start=1):
            folium.CircleMarker(
                location=[point.latitude, point.longitude],
                radius=6,
                color="orange" if route.get("manual_override") else "crimson",
                fill=True,
                fill_opacity=0.8,
                popup=f"#{index} {point.label} - {point.city}/{point.state}",
            ).add_to(map_view)

    components.html(map_view._repr_html_(), height=560)
