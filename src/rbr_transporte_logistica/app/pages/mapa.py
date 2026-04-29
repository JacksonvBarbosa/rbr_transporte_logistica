from __future__ import annotations

import folium
import pandas as pd
import streamlit as st
from folium import plugins

from rbr_transporte_logistica.app.dependencies import build_partner_controller
from rbr_transporte_logistica.app.theme import AZUL_CLARO, ROXO, TEAL, apply_theme, sidebar_nav
from rbr_transporte_logistica.core.database import db_session
from rbr_transporte_logistica.repositories.quote_repository import TabelaFreteRepo as TabelaFreteRepository

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

    last_route = st.session_state.get("last_route")
    last_simulation = st.session_state.get("last_simulation")
    selected_ids = st.session_state.get("selected_partner_ids", [])

    col_refresh, col_info = st.columns([1, 5])
    with col_refresh:
        if st.button("🔄 Atualizar mapa", key="refresh_map"):
            st.rerun()
    with col_info:
        if last_route:
            n_seg = len(last_route.get("segments", []))
            st.caption(f"Rota ativa: {n_seg} trecho(s) · {len(selected_ids)} parceiro(s) selecionado(s)")
        else:
            st.caption("Nenhuma rota simulada ainda. Va para Simulacao para calcular.")

    with db_session() as session:
        partner_controller = build_partner_controller(session)
        tabela_repo = TabelaFreteRepository(session)
        partners = partner_controller.list_partners(active_only=False)
        tabelas_ativas: dict[int, object] = {}
        for item in tabela_repo.listar_tabelas():
            if item.active and item.status == "ativa" and item.partner_id not in tabelas_ativas:
                tabelas_ativas[item.partner_id] = item

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    _ = (col_f2, col_f3, col_f4)
    with col_f1:
        filtro = st.radio("Exibir", ["Todos", "Ativos", "Com rota", "Sem coords"], horizontal=True)

    parceiros_filtrados = _filter_partners(partners, filtro)
    selected_partner_ids: set[int] = set(int(partner_id) for partner_id in selected_ids)
    segment_values: dict[int, dict[str, float | str]] = {}

    if last_route:
        for seg in last_route.get("segments", []):
            selected_partner_ids.add(seg.partner_id)
            if seg.partner_id not in segment_values:
                segment_values[seg.partner_id] = {
                    "price": 0.0,
                    "km": 0.0,
                    "rule_type": seg.rule_type,
                }
            segment_values[seg.partner_id]["price"] = float(segment_values[seg.partner_id]["price"]) + float(seg.price)
            segment_values[seg.partner_id]["km"] = float(segment_values[seg.partner_id]["km"]) + float(seg.distance_km)

    map_view = folium.Map(location=[-15.7, -47.9], zoom_start=5, tiles="CartoDB positron")

    for partner in parceiros_filtrados:
        if partner.latitude is None or partner.longitude is None:
            continue

        is_selected = partner.id in selected_partner_ids
        seg_info = segment_values.get(partner.id, {})
        tabela_ativa = tabelas_ativas.get(partner.id)
        latitude = float(partner.latitude)
        longitude = float(partner.longitude)
        tooltip = folium.Tooltip(
            _build_tooltip(partner, seg_info, is_selected, tabela_ativa),
            sticky=True,
        )

        if is_selected:
            label_html = f"""
            <div style="
                background:#042C53;
                color:#fff;
                font-size:10px;
                font-weight:600;
                padding:3px 8px;
                border-radius:12px;
                white-space:nowrap;
                border:1.5px solid #FFA500;
                box-shadow:0 2px 6px rgba(0,0,0,0.3);
                font-family:Inter,sans-serif;
            ">
                🚛 {partner.name}<br>
                <span style="color:#7DD3FC;font-weight:400;">
                    R$ {float(seg_info.get("price", 0.0)):.2f} · {float(seg_info.get("km", 0.0)):.0f} km
                </span>
            </div>
            """
            folium.Marker(
                location=[latitude, longitude],
                tooltip=tooltip,
                popup=folium.Popup(_build_popup(partner, seg_info, is_selected=True), max_width=240),
                icon=folium.DivIcon(
                    html=label_html,
                    icon_size=(180, 52),
                    icon_anchor=(90, 52),
                ),
            ).add_to(map_view)
            folium.CircleMarker(
                location=[latitude, longitude],
                radius=14,
                color="#FFA500",
                weight=2.5,
                fill=True,
                fill_color="#FFA500",
                fill_opacity=0.18,
            ).add_to(map_view)
        else:
            folium.CircleMarker(
                location=[latitude, longitude],
                radius=7,
                color="#185FA5",
                weight=2,
                fill=True,
                fill_color="#185FA5",
                fill_opacity=0.75,
                tooltip=tooltip,
                popup=folium.Popup(_build_popup(partner, {}, is_selected=False), max_width=200),
            ).add_to(map_view)

    if last_route and last_route.get("route_points"):
        coords = [
            [float(route_point.latitude), float(route_point.longitude)]
            for route_point in last_route["route_points"]
            if route_point.latitude is not None and route_point.longitude is not None
        ]
        if len(coords) >= 2:
            folium.PolyLine(
                locations=coords,
                color="#185FA5",
                weight=2.5,
                dash_array="8 5",
                opacity=0.85,
                tooltip="Rota simulada",
            ).add_to(map_view)
            ant_path = getattr(plugins, "AntPath", None)
            if ant_path is not None:
                ant_path(
                    locations=coords,
                    color="#185FA5",
                    weight=3,
                    delay=1200,
                    dash_array=[10, 20],
                    pulse_color="#BDD7EE",
                ).add_to(map_view)
            else:
                folium.PolyLine(
                    locations=coords,
                    color="#BDD7EE",
                    weight=1,
                    opacity=0.9,
                ).add_to(map_view)

    if last_simulation and last_simulation.get("origin") and last_simulation.get("destination"):
        folium.map.Marker(
            [-32, -70],
            icon=folium.DivIcon(
                html="<div style='background:white;padding:10px;border:1px solid #dce5f0;"
                "border-radius:10px;font-size:12px;'>"
                "<strong>Legenda</strong><br>Parceiro selecionado: laranja<br>Parceiro padrao: azul"
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

    dados: list[dict[str, object]] = []
    for partner in parceiros_filtrados:
        regras = list(partner.freight_rules or [])
        regra_principal = regras[0] if regras else None
        dados.append(
            {
                "Parceiro": partner.name,
                "Cidade": partner.city,
                "UF": partner.state,
                "Status": "Ativo" if partner.active else "Inativo",
                "Regras": len(regras),
                "Tipo regra": regra_principal.rule_type if regra_principal else "-",
                "Valor base": float(regra_principal.base_price) if regra_principal else 0.0,
                "Cobertura km": float(regra_principal.max_km) if regra_principal else 0.0,
                "Lat": f"{float(partner.latitude):.4f}" if partner.latitude is not None else "-",
                "Lon": f"{float(partner.longitude):.4f}" if partner.longitude is not None else "-",
            }
        )

    st.dataframe(
        pd.DataFrame(dados),
        use_container_width=True,
        hide_index=True,
        height=240,
        column_config={
            "Parceiro": st.column_config.TextColumn("Parceiro", width="medium"),
            "Cidade": st.column_config.TextColumn("Cidade", width="medium"),
            "UF": st.column_config.TextColumn("UF", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Regras": st.column_config.NumberColumn("Regras", width="small", format="%d"),
            "Tipo regra": st.column_config.TextColumn("Tipo regra", width="medium"),
            "Valor base": st.column_config.NumberColumn("Valor base", width="medium", format="R$ %.2f"),
            "Cobertura km": st.column_config.NumberColumn("Cobertura km", width="medium", format="%.0f km"),
            "Lat": st.column_config.TextColumn("Lat", width="small"),
            "Lon": st.column_config.TextColumn("Lon", width="small"),
        },
    )

    selected_partner = _resolve_selected_partner(parceiros_filtrados)
    if selected_partner is not None:
        coord_text = "-"
        if selected_partner.latitude is not None and selected_partner.longitude is not None:
            coord_text = f"{float(selected_partner.latitude):.4f}, {float(selected_partner.longitude):.4f}"
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
        if round(float(partner.latitude), 4) == round(float(lat), 4) and \
                round(float(partner.longitude), 4) == round(float(lng), 4):
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


def _build_tooltip(partner, seg_info: dict, is_selected: bool, tabela_ativa) -> str:
    cobertura_max = "-"
    valor_ref = "-"
    regras = sorted(list(partner.freight_rules or []), key=lambda rule: float(rule.max_km or 0))
    if regras:
        cobertura_max = f"{float(regras[-1].max_km):.0f} km"
        regra_base = regras[0]
        if regra_base.rule_type == "FIXED":
            valor_ref = f"R$ {float((regra_base.extra_config or {}).get('fixed_price', 0)):.2f} (base)"
        else:
            valor_ref = f"R$ {float(regra_base.base_price):.2f} (base)"

    rota_html = ""
    if is_selected and seg_info:
        rota_html = f"""
        <hr style="margin:5px 0;border:0.5px solid #334155;">
        <b style="color:#7DD3FC;">Na rota atual:</b><br>
        💰 R$ {float(seg_info['price']):.2f} &nbsp;·&nbsp; {float(seg_info['km']):.0f} km
        """

    tabela_html = ""
    if tabela_ativa is not None:
        tabela_html = f"<br>📄 Tabela ativa: <b style='color:#7DD3FC;'>{tabela_ativa.description}</b>"

    return f"""
    <div style="font-family:Inter,sans-serif;font-size:11px;
                background:#042C53;color:#CBD5E1;
                padding:8px 10px;border-radius:7px;
                min-width:180px;line-height:1.6;
                border:1px solid #1E3A5F;">
        <b style="color:#ffffff;font-size:12px;">{partner.name}</b><br>
        📍 {partner.city} / {partner.state}<br>
        📏 Cobertura máx: <b style="color:#7DD3FC;">{cobertura_max}</b><br>
        💵 Valor referência: <b style="color:#7DD3FC;">{valor_ref}</b><br>
        Status: {'<span style="color:#4ADE80;">✅ Ativo</span>'
                    if partner.active else '<span style="color:#F87171;">❌ Inativo</span>'}
        {tabela_html}
        {rota_html}
    </div>
    """


def _build_popup(partner, seg_info: dict, is_selected: bool) -> str:
    header_color = "#FFA500" if is_selected else "#185FA5"
    extra = ""
    if is_selected and seg_info:
        extra = f"""
        <hr style="margin:6px 0;border-color:#e2e8f0;">
        <b style="color:#0F6E56;">Rota selecionada</b><br>
        Valor: <b>R$ {float(seg_info['price']):.2f}</b><br>
        Distancia: <b>{float(seg_info['km']):.0f} km</b><br>
        Regra: <b>{seg_info['rule_type']}</b>
        """
    return f"""
    <div style="font-family:Inter,sans-serif;font-size:12px;min-width:160px;">
        <div style="background:{header_color};color:#fff;padding:6px 10px;
                    border-radius:6px 6px 0 0;font-weight:600;">
            {partner.name}
        </div>
        <div style="padding:8px 10px;">
            📍 {partner.city} / {partner.state}<br>
            Status: {'✅ Ativo' if partner.active else '❌ Inativo'}
            {extra}
        </div>
    </div>
    """
