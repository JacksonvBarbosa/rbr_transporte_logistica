from __future__ import annotations

import streamlit as st

from rbr_transporte_logistica.app.dependencies import build_partner_controller
from rbr_transporte_logistica.core.database import db_session


def render() -> None:
    st.header("Excluir Parceiro")
    st.caption("Revise os dados do parceiro antes de confirmar a exclusao definitiva.")

    with db_session() as session:
        controller = build_partner_controller(session)
        partners = controller.list_partners()
        if not partners:
            st.info("Nenhum parceiro cadastrado.")
            return

        partner_options = {
            f"{partner.name} ({partner.city}/{partner.state})": partner for partner in partners
        }
        selected_label = st.selectbox(
            "Selecione o parceiro para exclusao",
            list(partner_options.keys()),
            key="delete_partner_select",
        )
        selected_partner = partner_options[selected_label]

        st.write(f"Nome: {selected_partner.name}")
        st.write(f"Cidade: {selected_partner.city}")
        st.write(f"UF: {selected_partner.state}")
        st.write(f"Status: {'Ativo' if selected_partner.active else 'Inativo'}")
        st.write(f"Regras vinculadas: {len(selected_partner.freight_rules)}")
        st.warning(
            "A exclusao e irreversivel e tambem remove todas as regras de frete vinculadas."
        )

        confirmation_text = st.text_input(
            "Digite o nome do parceiro para confirmar a exclusao",
            key=f"delete_partner_confirmation_{selected_partner.id}",
        )
        can_delete = confirmation_text == selected_partner.name

        if st.button(
            "Confirmar exclusao",
            type="primary",
            key=f"confirm_partner_delete_{selected_partner.id}",
            disabled=not can_delete,
        ):
            try:
                controller.delete_partner(selected_partner.id)
                session.commit()
                st.session_state.pop("selected_partner_ids", None)
                st.success("Parceiro excluido com sucesso.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
