from __future__ import annotations

import streamlit as st

from rbr_transporte_logistica.app.pages import (
    mapa,
    orcamento,
    parceiro_crud,
    parceiro_exclusao,
    simulacao,
    upload,
)
from rbr_transporte_logistica.core.database import create_all

st.set_page_config(page_title="Frete System", page_icon="truck", layout="wide")


def main() -> None:
    create_all()
    st.title("Frete System")
    st.caption("Plataforma de calculo, simulacao e orcamento logistico.")

    pages = {
        "Parceiros": parceiro_crud.render,
        "Excluir Parceiro": parceiro_exclusao.render,
        "Upload": upload.render,
        "Simulacao": simulacao.render,
        "Mapa": mapa.render,
        "Orcamento": orcamento.render,
    }

    selection = st.sidebar.radio("Navegacao", list(pages.keys()))
    pages[selection]()


if __name__ == "__main__":
    main()
