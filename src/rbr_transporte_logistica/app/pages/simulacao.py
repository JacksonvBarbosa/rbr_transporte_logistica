from __future__ import annotations

import folium
import pandas as pd
import streamlit as st

from rbr_transporte_logistica.app.dependencies import (
    build_cliente_repository,
    build_freight_controller,
    build_partner_controller,
    build_quote_controller,
)
from rbr_transporte_logistica.app.theme import apply_theme, sidebar_nav
from rbr_transporte_logistica.core.database import db_session
from rbr_transporte_logistica.repositories.quote_repository import CotacaoRepo
from rbr_transporte_logistica.services.route_builder import default_segment_pickup_modes
from rbr_transporte_logistica.utils.geo_utils import (
    get_coordinates,
    get_coordinates_full_address,
    map_center,
)

try:
    from streamlit_folium import st_folium
except Exception:  # pragma: no cover
    st_folium = None


def _handle_route_error(message: str) -> None:
    st.session_state.pop("last_route", None)
    st.error(message)


def _sanitize_selected_partner_ids(session_state: dict, valid_ids: list[int]) -> list[int]:
    sanitized = [partner_id for partner_id in session_state.get("selected_partner_ids", []) if partner_id in valid_ids]
    session_state["selected_partner_ids"] = sanitized
    return sanitized


def render() -> None:
    apply_theme()
    sidebar_nav("Simulação")
    st.markdown("### Simulacao")

    with db_session() as session:
        freight_controller = build_freight_controller(session)
        partner_controller = build_partner_controller(session)
        quote_controller = build_quote_controller()
        quote_repo = CotacaoRepo(session)
        cliente_repo = build_cliente_repository(session)
        active_partners = partner_controller.list_partners(active_only=True)

        modo_endereco = st.radio(
            "Precisao da rota",
            ["Cidade / UF", "Endereco completo"],
            horizontal=True,
            help="Modo cidade usa geocodificacao por municipio. Modo endereco usa o CEP/logradouro exato.",
            index=0 if st.session_state.get("modo_endereco", "Cidade / UF") == "Cidade / UF" else 1,
        )
        st.session_state["modo_endereco"] = modo_endereco

        if modo_endereco == "Endereco completo":
            origem_cols = st.columns([2, 2, 1, 1, 1])
            end_origem = origem_cols[0].text_input("Endereco origem", value=st.session_state.get("end_origem", ""))
            cidade_origem = origem_cols[1].text_input("Cidade origem", value=st.session_state.get("origin_city", "Sao Paulo"))
            uf_origem = origem_cols[2].text_input("UF origem", value=st.session_state.get("origin_state", "SP"), max_chars=2)
            cep_origem = origem_cols[3].text_input("CEP origem", value=st.session_state.get("cep_origem", ""))
            _ = origem_cols[4]

            destino_cols = st.columns([2, 2, 1, 1, 1])
            end_destino = destino_cols[0].text_input("Endereco destino", value=st.session_state.get("end_destino", ""))
            cidade_destino = destino_cols[1].text_input("Cidade destino", value=st.session_state.get("destination_city", "Rio de Janeiro"))
            uf_destino = destino_cols[2].text_input("UF destino", value=st.session_state.get("destination_state", "RJ"), max_chars=2)
            cep_destino = destino_cols[3].text_input("CEP destino", value=st.session_state.get("cep_destino", ""))
            calculate_clicked = destino_cols[4].button("Calcular ->", key="calculate_simulation", type="primary")
        else:
            row = st.columns([2, 1, 2, 1, 1])
            end_origem = ""
            cep_origem = ""
            end_destino = ""
            cep_destino = ""
            cidade_origem = row[0].text_input("Cidade origem", value=st.session_state.get("origin_city", "Sao Paulo"))
            uf_origem = row[1].text_input("UF origem", value=st.session_state.get("origin_state", "SP"), max_chars=2)
            cidade_destino = row[2].text_input("Cidade destino", value=st.session_state.get("destination_city", "Rio de Janeiro"))
            uf_destino = row[3].text_input("UF destino", value=st.session_state.get("destination_state", "RJ"), max_chars=2)
            calculate_clicked = row[4].button("Calcular ->", key="calculate_simulation", type="primary")

        if calculate_clicked:
            try:
                if modo_endereco == "Endereco completo":
                    orig_lat, orig_lon = get_coordinates_full_address(end_origem, cidade_origem, uf_origem, cep_origem)
                    dest_lat, dest_lon = get_coordinates_full_address(end_destino, cidade_destino, uf_destino, cep_destino)
                else:
                    orig_lat, orig_lon = get_coordinates(cidade_origem, uf_origem)
                    dest_lat, dest_lon = get_coordinates(cidade_destino, uf_destino)

                st.session_state["origin_city"] = cidade_origem
                st.session_state["origin_state"] = uf_origem
                st.session_state["destination_city"] = cidade_destino
                st.session_state["destination_state"] = uf_destino
                st.session_state["end_origem"] = end_origem
                st.session_state["cep_origem"] = cep_origem
                st.session_state["end_destino"] = end_destino
                st.session_state["cep_destino"] = cep_destino
                st.session_state["origem_coords"] = (orig_lat, orig_lon)
                st.session_state["destino_coords"] = (dest_lat, dest_lon)
                st.session_state["modo_endereco_atual"] = modo_endereco

                result = freight_controller.simulate(
                    origin_city=cidade_origem,
                    origin_state=uf_origem,
                    destination_city=cidade_destino,
                    destination_state=uf_destino,
                    optimization_mode=st.session_state.get("optimization_mode", "cost"),
                    origin_coords=(orig_lat, orig_lon),
                    destination_coords=(dest_lat, dest_lon),
                )
                st.session_state["last_simulation"] = result
                st.session_state.pop("last_route", None)
                st.session_state.pop("last_quote", None)
                st.session_state["selected_partner_ids"] = result.get("valid_partner_ids", [])
                if result.get("selected_route"):
                    st.session_state["last_route"] = result["selected_route"]
                    st.session_state["selected_partner_ids"] = result["selected_route"]["selected_partner_ids"]
                    st.session_state["selected_segment_pickup_modes"] = result["selected_route"]["segment_pickup_modes"]
                if result.get("error"):
                    _handle_route_error(result["message"])
                    return
            except ValueError as exc:
                _handle_route_error(str(exc))
                return

        simulation = st.session_state.get("last_simulation")
        if not simulation:
            st.info("Informe origem e destino para calcular a rota.")
            return

        comparison_df = pd.DataFrame(
            [
                {
                    "Parceiro": row.partner_name,
                    "Cidade/UF": f"{row.city}/{row.state}",
                    "Regra ativa": row.rule_type,
                    "Prazo": row.deadline_days,
                    "Valor": row.price,
                }
                for row in simulation.get("results", [])
            ]
        )
        st.markdown("#### Parceiros disponiveis")
        if comparison_df.empty:
            st.info("Nenhum parceiro conseguiu atender a rota diretamente.")
        else:
            st.dataframe(comparison_df, use_container_width=True, hide_index=True)

        valid_ids = [partner.id for partner in active_partners]
        sanitized = _sanitize_selected_partner_ids(st.session_state, valid_ids)
        partner_lookup = {partner.id: partner for partner in active_partners}
        selected_partner_ids = st.multiselect(
            "Selecionar parceiros da rota em ordem",
            options=valid_ids,
            default=sanitized,
            key="selected_partner_ids_multiselect",
            format_func=lambda partner_id: f"{partner_lookup[partner_id].name} ({partner_lookup[partner_id].city}/{partner_lookup[partner_id].state})",
        )
        st.session_state["selected_partner_ids"] = [partner_id for partner_id in selected_partner_ids if partner_id in valid_ids]

        if st.button("Montar rota multi-trecho", key="build_multi_leg_route", type="primary"):
            selected_partners = [partner_lookup[partner_id] for partner_id in st.session_state["selected_partner_ids"]]
            without_coordinates = [partner.name for partner in selected_partners if partner.latitude is None or partner.longitude is None]
            if without_coordinates:
                st.error(f"Parceiros sem coordenadas: {', '.join(without_coordinates)}")
            else:
                pickup_modes = st.session_state.get(
                    "selected_segment_pickup_modes",
                    default_segment_pickup_modes(len(selected_partners)),
                )
                try:
                    route = freight_controller.simulate_multi_leg(
                        origin_city=simulation["origin"].city,
                        origin_state=simulation["origin"].state,
                        destination_city=simulation["destination"].city,
                        destination_state=simulation["destination"].state,
                        partner_ids=st.session_state["selected_partner_ids"],
                        segment_pickup_modes=pickup_modes,
                        optimization_mode=st.session_state.get("optimization_mode", "cost"),
                        origin_coords=st.session_state.get("origem_coords"),
                        destination_coords=st.session_state.get("destino_coords"),
                    )
                    if route.get("error"):
                        _handle_route_error(route["message"])
                        return
                    st.session_state["last_route"] = route
                    st.session_state["last_quote"] = None
                    st.success("Rota multi-trecho calculada com sucesso.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

        route = st.session_state.get("last_route")
        if not route:
            return

        st.markdown("#### Trechos calculados")
        segments_df = pd.DataFrame(
            [
                {
                    "Trecho": segment.segment_order,
                    "Parceiro": segment.partner_name,
                    "Origem": segment.origin_label,
                    "Destino": segment.destination_label,
                    "KM": segment.distance_km,
                    "Valor": segment.price,
                    "Prazo": segment.segment_days,
                    "Regra": segment.rule_type,
                }
                for segment in route["segments"]
            ]
        )
        st.dataframe(segments_df, use_container_width=True, hide_index=True)

        map_points = [(point.latitude, point.longitude) for point in route["route_points"]]
        folium_map = folium.Map(location=map_center(map_points), zoom_start=5, tiles="CartoDB positron")
        for point in route["route_points"]:
            folium.Marker(location=[point.latitude, point.longitude], tooltip=point.label).add_to(folium_map)
        folium.PolyLine(
            [(point.latitude, point.longitude) for point in route["physical_path_points"]],
            color="#185FA5",
            weight=3,
        ).add_to(folium_map)
        if st_folium:
            st_folium(folium_map, width=None, height=420)
        else:
            st.components.v1.html(folium_map._repr_html_(), height=420)

        st.markdown("#### Painel de fechamento")
        icms = st.number_input("ICMS (%)", min_value=0.0, value=float(st.session_state.get("quote_icms", 12.0)), step=0.5)
        iss = st.number_input("ISS (%)", min_value=0.0, value=float(st.session_state.get("quote_iss", 5.0)), step=0.5)
        margin = st.number_input("Margem (%)", min_value=0.0, value=float(st.session_state.get("quote_margin", 15.0)), step=0.5)
        st.session_state["quote_icms"] = icms
        st.session_state["quote_iss"] = iss
        st.session_state["quote_margin"] = margin

        clientes = cliente_repo.listar()
        cliente_selecionado = None
        if not clientes:
            st.warning("Nenhum cliente cadastrado. Cadastre um cliente antes de fechar o frete.")
            if st.button("Ir para cadastro de clientes", key="go_to_clientes"):
                st.session_state["current_page"] = "Clientes"
                st.rerun()
        else:
            opcoes = {f"{cliente.nome} - {cliente.cpf_cnpj or cliente.email or 'sem doc'}": cliente for cliente in clientes}
            label_sel = st.selectbox(
                "Cliente *",
                options=list(opcoes.keys()),
                index=None,
                placeholder="Selecione o cliente...",
            )
            cliente_selecionado = opcoes[label_sel] if label_sel else None

        freight_gross = round(sum(float(segment.price) for segment in route["segments"]), 2)
        icms_value = round(freight_gross * (icms / 100), 2)
        iss_value = round(freight_gross * (iss / 100), 2)
        margin_value = round(freight_gross * (margin / 100), 2)
        total_value = round(freight_gross + icms_value + iss_value + margin_value, 2)
        quote_data = quote_controller.create_quote(
            origin=f"{route['origin'].city}/{route['origin'].state}",
            destination=f"{route['destination'].city}/{route['destination'].state}",
            direct_distance_km=float(route["direct_distance_km"]),
            segments=route["segments"],
            tax_rate=(icms + iss) / 100,
            margin_rate=margin / 100,
            additional_fee=0.0,
        )
        st.session_state["last_quote"] = quote_data

        summary_cols = st.columns(6)
        summary_cols[0].metric("Frete bruto", f"R$ {freight_gross:,.2f}")
        summary_cols[1].metric("ICMS", f"R$ {icms_value:,.2f}")
        summary_cols[2].metric("ISS", f"R$ {iss_value:,.2f}")
        summary_cols[3].metric("Margem", f"R$ {margin_value:,.2f}")
        summary_cols[4].metric("Total ao cliente", f"R$ {total_value:,.2f}")
        summary_cols[5].metric("Prazo total", f"{route['total_deadline_days']} dias")

        pdf_bytes = quote_controller.export_pdf(quote_data)
        excel_bytes = quote_controller.export_excel(quote_data)
        buttons = st.columns(3)
        buttons[0].download_button(
            "Baixar PDF",
            data=pdf_bytes,
            file_name="proposta_frete.pdf",
            mime="application/pdf",
        )
        buttons[1].download_button(
            "Baixar Excel",
            data=excel_bytes,
            file_name="proposta_frete.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        fechar_disabled = cliente_selecionado is None
        if buttons[2].button("✅ Fechar frete", key="close_freight_button", type="primary", disabled=fechar_disabled):
            quote = quote_repo.criar(
                customer_name=cliente_selecionado.nome if cliente_selecionado else "",
                origin=f"{route['origin'].city}/{route['origin'].state}",
                destination=f"{route['destination'].city}/{route['destination'].state}",
                route_label=" -> ".join(point.label for point in route["route_points"]),
                partner_id=route["selected_partner_ids"][0] if route["selected_partner_ids"] else None,
                partner_name=", ".join(segment.partner_name for segment in route["segments"]),
                status="fechado",
                freight_gross=freight_gross,
                icms_rate=icms / 100,
                icms_value=icms_value,
                iss_rate=iss / 100,
                iss_value=iss_value,
                margin_rate=margin / 100,
                margin_value=margin_value,
                total_value=total_value,
                total_deadline_days=route["total_deadline_days"],
                direct_distance_km=float(route["direct_distance_km"]),
                route_distance_km=float(route["total_distance_km"]),
                items=route["segments"],
            )
            if cliente_selecionado is not None:
                quote.cliente_id = cliente_selecionado.id
                quote.customer_name = cliente_selecionado.nome
            session.commit()
            st.session_state["last_closed_quote_id"] = quote.id
            st.success("Frete fechado! Dashboard atualizado.")
            st.rerun()
