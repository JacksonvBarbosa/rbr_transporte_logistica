from __future__ import annotations

import folium
import pandas as pd
import streamlit as st

from rbr_transporte_logistica.app.dependencies import build_partner_controller
from rbr_transporte_logistica.app.theme import AZUL_CLARO, ROXO, TEAL, apply_theme, sidebar_nav
from rbr_transporte_logistica.core.database import db_session

try:
    from streamlit_folium import st_folium
except Exception:  # pragma: no cover
    st_folium = None

REGION_COLORS = {
    "NORTE": ROXO,
    "NORDESTE": "#C76A16",
    "CENTRO-OESTE": TEAL,
    "SUDESTE": AZUL_CLARO,
    "SUL": "#1F7A5A",
}


def render() -> None:
    apply_theme()
    sidebar_nav("Mapa de Rotas")
    st.markdown("### Mapa de Rotas")

    with db_session() as session:
        partner_controller = build_partner_controller(session)
        partners = partner_controller.list_partners(active_only=False)

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    _ = (col_f2, col_f3, col_f4)
    with col_f1:
        filtro = st.radio("Exibir", ["Todos", "Ativos", "Com rota", "Sem coords"], horizontal=True)

    parceiros_filtrados = _filter_partners(partners, filtro)
    route = st.session_state.get("last_route")
    map_view = folium.Map(location=[-15.7, -47.9], zoom_start=5, tiles="CartoDB positron")

    for partner in parceiros_filtrados:
        if partner.latitude is None or partner.longitude is None:
            continue
        popup_html = _partner_popup(partner)
        folium.Marker(
            location=[partner.latitude, partner.longitude],
            popup=folium.Popup(popup_html, max_width=320),
            tooltip=partner.name,
            icon=folium.Icon(color="blue", icon="truck", prefix="fa"),
        ).add_to(map_view)

    if route:
        folium.PolyLine(
            [(point.latitude, point.longitude) for point in route["physical_path_points"]],
            color="#185FA5",
            weight=2.5,
            dash_array="8 6",
        ).add_to(map_view)

    folium.map.Marker(
        [-32, -70],
        icon=folium.DivIcon(
            html="<div style='background:white;padding:10px;border:1px solid #dce5f0;border-radius:10px;font-size:12px;'>"
            "<strong>Legenda</strong><br>Norte: roxo<br>Nordeste: laranja<br>Centro-Oeste: verde<br>Sudeste: azul<br>Sul: verde escuro"
            "</div>"
        ),
    ).add_to(map_view)

    if st_folium:
        result = st_folium(
            map_view,
            width=None,
            height=480,
            returned_objects=["last_object_clicked"],
        )
        clicked = (result or {}).get("last_object_clicked")
        if clicked and "lat" in clicked and "lng" in clicked:
            st.session_state["selected_map_coords"] = (clicked["lat"], clicked["lng"])
    else:
        st.components.v1.html(map_view._repr_html_(), height=480)

    st.markdown("---")
    st.markdown("**Parceiros no mapa**")

    dados = []
    for partner in parceiros_filtrados:
        regras = list(partner.freight_rules or [])
        dados.append(
            {
                "Parceiro": partner.name,
                "Cidade": partner.city,
                "UF": partner.state,
                "Status": "Ativo" if partner.active else "Inativo",
                "Regras": len(regras),
                "Tipo principal": regras[0].rule_type if regras else "—",
                "Lat": f"{partner.latitude:.4f}" if partner.latitude is not None else "—",
                "Lon": f"{partner.longitude:.4f}" if partner.longitude is not None else "—",
            }
        )

    st.dataframe(
        pd.DataFrame(dados),
        use_container_width=True,
        hide_index=True,
        height=220,
        column_config={
            "Status": st.column_config.TextColumn("Status"),
            "Regras": st.column_config.NumberColumn("Regras", format="%d"),
        },
    )

    selected_partner = _resolve_selected_partner(parceiros_filtrados)
    if selected_partner is not None:
        coord_text = "—"
        if selected_partner.latitude is not None and selected_partner.longitude is not None:
            coord_text = f"{selected_partner.latitude:.4f}, {selected_partner.longitude:.4f}"
        st.info(
            "Parceiro selecionado: "
            f"{selected_partner.name} | {selected_partner.city}/{selected_partner.state} | "
            f"Status: {'Ativo' if selected_partner.active else 'Inativo'} | "
            f"Coords: {coord_text}"
        )
        if st.button(
            "Simular rota com este parceiro ->",
            key=f"simulate_from_map_{selected_partner.id}",
            type="primary",
        ):
            st.session_state["preselected_partner"] = selected_partner.id
            st.session_state["selected_partner_ids"] = [selected_partner.id]
            st.session_state["current_page"] = "Simulação"
            st.rerun()


def _resolve_selected_partner(partners: list) -> object | None:
    coords = st.session_state.get("selected_map_coords")
    if not coords:
        return None
    lat, lng = coords
    for partner in partners:
        if partner.latitude is None or partner.longitude is None:
            continue
        if round(float(partner.latitude), 4) == round(float(lat), 4) and round(float(partner.longitude), 4) == round(float(lng), 4):
            return partner
    return None


def _filter_partners(partners: list, mode: str) -> list:
    route_ids = set((st.session_state.get("last_route") or {}).get("selected_partner_ids", []))
    if mode == "Ativos":
        return [partner for partner in partners if partner.active]
    if mode == "Com rota":
        return [partner for partner in partners if partner.id in route_ids]
    if mode == "Sem coords":
        return [partner for partner in partners if partner.latitude is None or partner.longitude is None]
    return partners


def _partner_popup(partner) -> str:
    rule_list = "".join(
        f"<li>{rule.rule_type} • {rule.deadline_days} dias • {float(rule.max_km):,.0f} km</li>"
        for rule in partner.freight_rules
    )
    return (
        f"<strong>{partner.name}</strong><br>"
        f"{partner.city}/{partner.state}<br>"
        f"Status: {'Ativo' if partner.active else 'Inativo'}<br>"
        f"Regras: {len(partner.freight_rules)}"
        f"<ul>{rule_list}</ul>"
    )
