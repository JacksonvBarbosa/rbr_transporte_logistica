from __future__ import annotations

from typing import Any

import streamlit as st

from rbr_transporte_logistica.app.dependencies import build_partner_controller
from rbr_transporte_logistica.app.theme import apply_theme, sidebar_nav
from rbr_transporte_logistica.core.database import db_session
from rbr_transporte_logistica.services.partner_service import PartnerService


def render() -> None:
    apply_theme()
    sidebar_nav("Parceiros")
    st.markdown("### Parceiros")

    with db_session() as session:
        controller = build_partner_controller(session)

        with st.expander("➕ Novo parceiro", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            name = col1.text_input("Nome", key="new_partner_name")
            city = col2.text_input("Cidade", key="new_partner_city")
            state = col3.text_input("UF", key="new_partner_state", max_chars=2)
            active = col4.checkbox("Ativo", key="new_partner_active", value=True)
            if st.button("Criar parceiro", key="create_partner_button", type="primary"):
                try:
                    controller.create_partner(name=name, city=city, state=state, active=active)
                    session.commit()
                    st.success("Parceiro criado com sucesso.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
            st.caption("Coordenadas geradas automaticamente.")

        st.markdown("### Parceiros cadastrados")
        partners = controller.list_partners()
        if not partners:
            st.info("Nenhum parceiro cadastrado.")
            return

        for partner in partners:
            with st.expander(f"{partner.name} — {partner.city}/{partner.state}", expanded=False):
                coords = "Coordenadas indisponiveis"
                if partner.latitude is not None and partner.longitude is not None:
                    coords = f"{partner.latitude:.6f}, {partner.longitude:.6f}"
                st.caption(f"Coordenadas: {coords} | Status: {'Ativo' if partner.active else 'Inativo'}")

                edit_cols = st.columns(4)
                edit_name = edit_cols[0].text_input("Nome", value=partner.name, key=f"partner_name_{partner.id}")
                edit_city = edit_cols[1].text_input("Cidade", value=partner.city, key=f"partner_city_{partner.id}")
                edit_state = edit_cols[2].text_input("UF", value=partner.state, max_chars=2, key=f"partner_state_{partner.id}")
                edit_active = edit_cols[3].checkbox("Ativo", value=partner.active, key=f"partner_active_{partner.id}")
                action_cols = st.columns(2)
                if action_cols[0].button("Salvar alterações", key=f"save_partner_{partner.id}"):
                    try:
                        controller.update_partner(
                            partner.id,
                            name=edit_name,
                            city=edit_city,
                            state=edit_state,
                            active=edit_active,
                        )
                        session.commit()
                        st.success("Parceiro atualizado.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
                toggle_label = "Desativar" if partner.active else "Ativar"
                if action_cols[1].button(toggle_label, key=f"toggle_partner_{partner.id}"):
                    controller.set_partner_active(partner.id, not partner.active)
                    session.commit()
                    st.rerun()

                st.divider()
                st.markdown("**Regras de frete deste parceiro**")
                if not partner.freight_rules:
                    st.info("Esse parceiro ainda nao possui regras.")
                else:
                    for rule in partner.freight_rules:
                        chip_cols = st.columns([5, 1])
                        chip_cols[0].markdown(_rule_description(rule), unsafe_allow_html=True)
                        if chip_cols[1].button("✕ Excluir regra", key=f"delete_rule_{partner.id}_{rule.id}"):
                            controller.delete_rule(rule.id)
                            session.commit()
                            st.success("Regra excluida.")
                            st.rerun()

                st.markdown("**Adicionar nova regra**")
                payload = _render_rule_fields(f"partner_rule_{partner.id}")
                if st.button("Adicionar regra", key=f"add_rule_{partner.id}", type="primary"):
                    try:
                        controller.add_rule(partner_id=partner.id, **payload)
                        session.commit()
                        st.success("Regra criada com sucesso.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))


def _rule_description(rule: Any) -> str:
    values = []
    if rule.rule_type == "LINEAR":
        values.append(f"Base R$ {float(rule.base_price):,.2f}")
        values.append(f"+ R$ {float(rule.price_per_km):,.2f}/km")
    elif rule.rule_type == "FIXED":
        values.append(f"Fixo R$ {float((rule.extra_config or {}).get('fixed_price', 0)):,.2f}")
    else:
        tiers = ", ".join(
            f"ate {tier['up_to_km']} km: R$ {tier['price']:,.2f}"
            for tier in (rule.extra_config or {}).get("tiers", [])
        )
        values.append(tiers or "Sem faixas")
    return (
        "<div class='rbr-card'>"
        f"<strong>{rule.rule_type}</strong> • Prazo {rule.deadline_days} dias • Cobertura {float(rule.max_km):,.0f} km"
        f"<br>{' | '.join(values)}"
        "</div>"
    )


def _render_rule_fields(prefix: str, rule=None) -> dict[str, Any]:
    existing_rule_type = rule.rule_type if rule else "LINEAR"
    existing_config = rule.extra_config or {} if rule else {}
    col1, col2 = st.columns(2)
    rule_type = col1.selectbox(
        "Tipo de regra",
        ["LINEAR", "FIXED", "TIERED"],
        key=f"type_{prefix}",
        index=["LINEAR", "FIXED", "TIERED"].index(existing_rule_type),
    )
    max_km_default = float(rule.max_km if rule else 300.0)
    max_km = float(col2.number_input("Cobertura maxima (km)", min_value=1.0, value=max_km_default, step=10.0, key=f"max_km_{prefix}"))
    st.caption(f"Prazo calculado automaticamente: {PartnerService._calculate_rule_deadline_days(max_km)} dias")

    if rule_type == "LINEAR":
        linear_cols = st.columns(2)
        return {
            "rule_type": "LINEAR",
            "base_price": float(linear_cols[0].number_input("Preco base", min_value=0.0, value=float(rule.base_price if rule else 100.0), step=10.0, key=f"base_{prefix}")),
            "price_per_km": float(linear_cols[1].number_input("Preco por km", min_value=0.0, value=float(rule.price_per_km if rule else 1.5), step=0.1, key=f"price_km_{prefix}")),
            "max_km": max_km,
            "extra_config": None,
        }

    if rule_type == "FIXED":
        fixed_price = float(st.number_input("Preco fixo", min_value=0.0, value=float(existing_config.get("fixed_price", 250.0)), step=10.0, key=f"fixed_price_{prefix}"))
        return {
            "rule_type": "FIXED",
            "base_price": 0.0,
            "price_per_km": 0.0,
            "max_km": max_km,
            "extra_config": {"fixed_price": fixed_price},
        }

    default_tiers = existing_config.get("tiers", [{"up_to_km": 100.0, "price": 200.0}, {"up_to_km": 300.0, "price": 420.0}])
    tier_count = int(st.number_input("Quantidade de faixas", min_value=1, max_value=5, value=len(default_tiers), step=1, key=f"tier_count_{prefix}"))
    tiers = []
    for index in range(tier_count):
        tier = default_tiers[index] if index < len(default_tiers) else {"up_to_km": 100.0, "price": 150.0}
        tier_cols = st.columns(2)
        tiers.append(
            {
                "up_to_km": float(tier_cols[0].number_input(f"Faixa {index + 1} ate km", min_value=1.0, value=float(tier["up_to_km"]), step=10.0, key=f"tier_km_{prefix}_{index}")),
                "price": float(tier_cols[1].number_input(f"Preco faixa {index + 1}", min_value=0.0, value=float(tier["price"]), step=10.0, key=f"tier_price_{prefix}_{index}")),
            }
        )
    return {
        "rule_type": "TIERED",
        "base_price": 0.0,
        "price_per_km": 0.0,
        "max_km": max_km,
        "extra_config": {"tiers": tiers},
    }
