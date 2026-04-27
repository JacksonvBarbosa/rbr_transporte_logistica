from __future__ import annotations

import streamlit as st

from rbr_transporte_logistica.app.pages import (
    dashboard,
    mapa,
    orcamento,
    parceiro_crud,
    parceiro_exclusao,
    simulacao,
    upload,
)
from rbr_transporte_logistica.core.database import create_all

st.set_page_config(
    layout="wide",
    page_title="RBR Logística",
    page_icon="🚛",
    initial_sidebar_state="expanded",
)

PAGES = {
    "Dashboard": dashboard.render,
    "Parceiros": parceiro_crud.render,
    "Simulação": simulacao.render,
    "Mapa de Rotas": mapa.render,
    "Orçamentos": orcamento.render,
    "Upload de Tabelas": upload.render,
    "Excluir Parceiro": parceiro_exclusao.render,
}


def main() -> None:
    create_all()
    current_page = st.session_state.get("current_page", "Dashboard")
    if current_page not in PAGES:
        current_page = "Dashboard"
        st.session_state["current_page"] = current_page
    PAGES[current_page]()


if __name__ == "__main__":
    main()
