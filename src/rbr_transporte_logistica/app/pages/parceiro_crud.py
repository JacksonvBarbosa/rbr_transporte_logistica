from __future__ import annotations

from typing import Any

import streamlit as st

from rbr_transporte_logistica.app.dependencies import build_partner_controller
from rbr_transporte_logistica.core.database import db_session
from rbr_transporte_logistica.services.partner_service import PartnerService


def render() -> None:
    st.header("Parceiros e Regras")
    st.caption("Cadastre parceiros com geolocalizacao automatica e gerencie regras sem JSON manual.")

    with db_session() as session:
        controller = build_partner_controller(session)

        with st.expander("Novo parceiro", expanded=True):
            with st.form("create_partner_form"):
                col1, col2, col3, col4 = st.columns(4)
                name = col1.text_input("Nome do parceiro")
                city = col2.text_input("Cidade")
                state = col3.text_input("UF", max_chars=2)
                active = col4.checkbox("Ativo", value=True)
                submitted = st.form_submit_button("Criar parceiro", type="primary")
                if submitted:
                    try:
                        controller.create_partner(
                            name=name,
                            city=city,
                            state=state,
                            active=active,
                        )
                        session.commit()
                        st.success("Parceiro criado com coordenadas automaticas.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

        partners = controller.list_partners()
        if not partners:
            st.info("Nenhum parceiro cadastrado.")
            return

        st.subheader("Nova regra de frete")
        partner_options = {
            f"{partner.name} ({partner.city}/{partner.state})": partner.id for partner in partners
        }
        selected_label = st.selectbox("Selecione o parceiro", list(partner_options.keys()))
        selected_partner_id = partner_options[selected_label]
        _render_rule_create_form(controller, session, selected_partner_id)

        st.subheader("Parceiros cadastrados")
        for partner in partners:
            with st.expander(f"{partner.name} - {partner.city}/{partner.state}", expanded=False):
                if partner.latitude is not None and partner.longitude is not None:
                    coords_str = f"{partner.latitude:.6f}, {partner.longitude:.6f}"
                else:
                    coords_str = "Coordenadas não disponíveis"
                st.caption(
                    f"Coordenadas: {coords_str} | "
                    f"Status: {'Ativo' if partner.active else 'Inativo'}"
                )
                _render_partner_update_form(controller, session, partner)
                _render_rule_management(controller, session, partner)


def _render_partner_update_form(controller, session, partner) -> None:
    with st.form(f"partner_edit_{partner.id}"):
        col1, col2, col3, col4 = st.columns(4)
        name = col1.text_input("Nome", value=partner.name)
        city = col2.text_input("Cidade", value=partner.city)
        state = col3.text_input("UF", value=partner.state, max_chars=2)
        active = col4.checkbox("Ativo", value=partner.active)
        save = st.form_submit_button("Salvar alteracoes")
        if save:
            try:
                controller.update_partner(
                    partner.id,
                    name=name,
                    city=city,
                    state=state,
                    active=active,
                )
                session.commit()
                st.success("Parceiro atualizado.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    col1, _ = st.columns(2)
    toggle_label = "Desativar" if partner.active else "Ativar"
    if col1.button(toggle_label, key=f"toggle_partner_{partner.id}"):
        try:
            controller.set_partner_active(partner.id, not partner.active)
            session.commit()
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))


def _render_rule_create_form(controller, session, partner_id: int) -> None:
    with st.form("create_rule_form"):
        payload = _render_rule_fields("create")
        submitted = st.form_submit_button("Criar regra")
        if submitted:
            try:
                controller.add_rule(partner_id=partner_id, **payload)
                session.commit()
                st.success("Regra criada com sucesso.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


def _render_rule_management(controller, session, partner) -> None:
    st.markdown("**Regras de frete**")
    if not partner.freight_rules:
        st.info("Esse parceiro ainda nao possui regras.")
        return

    for rule in partner.freight_rules:
        with st.container(border=True):
            st.write(
                f"Regra #{rule.id} | Tipo: {rule.rule_type} | Prazo: {rule.deadline_days} dias | "
                f"Cobertura: {rule.max_km} km"
            )
            with st.form(f"edit_rule_{rule.id}"):
                payload = _render_rule_fields(f"rule_{rule.id}", rule=rule)
                save_rule = st.form_submit_button("Salvar regra")
                if save_rule:
                    try:
                        controller.update_rule(rule.id, **payload)
                        session.commit()
                        st.success("Regra atualizada.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))


def _render_rule_fields(prefix: str, rule=None) -> dict[str, Any]:
    existing_rule_type = rule.rule_type if rule else "LINEAR"
    existing_config = rule.extra_config or {} if rule else {}

    col1, col2 = st.columns(2)
    rule_type = col1.selectbox("Tipo de regra", ["LINEAR", "FIXED", "TIERED"],
                               key=f"type_{prefix}", index=["LINEAR", "FIXED", "TIERED"].index(existing_rule_type))
    max_km_default = float(rule.max_km if rule else 300.0)
    max_km = float(
        col2.number_input(
            "Cobertura maxima (km)",
            min_value=1.0,
            value=max_km_default,
            step=10.0,
            key=f"max_km_{prefix}",
        )
    )
    auto_deadline_days = PartnerService._calculate_rule_deadline_days(max_km)
    st.caption(f"Prazo calculado automaticamente: {auto_deadline_days} dias")

    if rule_type == "LINEAR":
        linear_cols = st.columns(2)
        base_price = float(
            linear_cols[0].number_input(
                "Preco base",
                min_value=0.0,
                value=float(rule.base_price if rule else 100.0),
                step=10.0,
                key=f"base_{prefix}",
            )
        )
        price_per_km = float(
            linear_cols[1].number_input(
                "Preco por km",
                min_value=0.0,
                value=float(rule.price_per_km if rule else 1.5),
                step=0.1,
                key=f"price_km_{prefix}",
            )
        )
        return {
            "rule_type": "LINEAR",
            "base_price": base_price,
            "price_per_km": price_per_km,
            "max_km": max_km,
            "extra_config": None,
        }

    if rule_type == "FIXED":
        fixed_price = float(
            st.number_input(
                "Preco fixo",
                min_value=0.0,
                value=float(existing_config.get("fixed_price", 250.0)),
                step=10.0,
                key=f"fixed_price_{prefix}",
            )
        )
        return {
            "rule_type": "FIXED",
            "base_price": 0.0,
            "price_per_km": 0.0,
            "max_km": max_km,
            "extra_config": {"fixed_price": fixed_price},
        }

    default_tiers = existing_config.get(
        "tiers",
        [{"up_to_km": 100.0, "price": 200.0}, {"up_to_km": 300.0, "price": 420.0}],
    )
    tier_count = int(
        st.number_input(
            "Quantidade de faixas",
            min_value=1,
            max_value=5,
            value=len(default_tiers),
            step=1,
            key=f"tier_count_{prefix}",
        )
    )
    tiers = []
    for index in range(tier_count):
        tier = default_tiers[index] if index < len(default_tiers) else {"up_to_km": 100.0, "price": 150.0}
        tier_cols = st.columns(2)
        km_limit = float(
            tier_cols[0].number_input(
                f"Faixa {index + 1} ate km",
                min_value=1.0,
                value=float(tier["up_to_km"]),
                step=10.0,
                key=f"tier_km_{prefix}_{index}",
            )
        )
        price = float(
            tier_cols[1].number_input(
                f"Preco faixa {index + 1}",
                min_value=0.0,
                value=float(tier["price"]),
                step=10.0,
                key=f"tier_price_{prefix}_{index}",
            )
        )
        tiers.append({"up_to_km": km_limit, "price": price})

    return {
        "rule_type": "TIERED",
        "base_price": 0.0,
        "price_per_km": 0.0,
        "max_km": max_km,
        "extra_config": {"tiers": tiers},
    }
