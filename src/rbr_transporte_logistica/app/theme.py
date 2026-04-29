from __future__ import annotations

import streamlit as st

AZUL_ESCURO = "#042C53"
AZUL_MEDIO = "#0C447C"
AZUL_CLARO = "#185FA5"
AZUL_SUAVE = "#E6F1FB"
TEAL = "#0F6E56"
AMBAR = "#854F0B"
ROXO = "#533AB7"
VERMELHO = "#A32D2D"
CINZA_BG = "#F7F9FC"


def apply_theme() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="css"], [data-testid="stAppViewContainer"], .stApp {{
            font-family: 'Inter', sans-serif;
        }}
        .stApp {{
            background: {CINZA_BG};
        }}
        /* Oculta APENAS o header, nunca o collapsedControl */
        header[data-testid="stHeader"] {{
            display: none !important;
        }}
        /* Botão de reabrir sidebar - SEMPRE visível, qualquer estado */
        [data-testid="collapsedControl"] {{
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            z-index: 999999 !important;
            position: fixed !important;
        }}
        [data-testid="collapsedControl"] svg {{
            fill: {AZUL_MEDIO} !important;
            color: {AZUL_MEDIO} !important;
        }}
        [data-testid="collapsedControl"]:hover {{
            background: {AZUL_SUAVE} !important;
            border-radius: 6px !important;
        }}
        section[data-testid="stSidebar"] {{
            background: {AZUL_ESCURO};
            color: white;
            padding-top: 0.25rem;
        }}
        section[data-testid="stSidebar"] * {{
            color: white;
        }}
        section[data-testid="stSidebar"] > div > div > div {{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }}
        section[data-testid="stSidebar"] .st-emotion-cache-16txtl3,
        section[data-testid="stSidebar"] .st-emotion-cache-1cypcdb {{
            padding-top: 0.25rem;
            padding-bottom: 0.75rem;
        }}
        /* Remove gaps extras entre elementos do sidebar */
        section[data-testid="stSidebar"] .stButton {{
            margin-bottom: 0 !important;
            margin-top: 0 !important;
            padding: 0 !important;
            line-height: 1 !important;
        }}
        section[data-testid="stSidebar"] .element-container {{
            margin-bottom: 0 !important;
            margin-top: 0 !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }}
        section[data-testid="stSidebar"] .block-container {{
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            gap: 0 !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
            gap: 0 !important;
        }}
        /* Esconde o texto duplicado do botão invisível de navegação,
           mantendo apenas o div estilizado acima */
        section[data-testid="stSidebar"] .stButton > button {{
            position: relative !important;
            margin-top: -36px !important;
            height: 36px !important;
            opacity: 0 !important;
            width: 100% !important;
            cursor: pointer !important;
            z-index: 10 !important;
            padding: 0 !important;
            min-height: 36px !important;
            border: none !important;
            box-shadow: none !important;
            background: transparent !important;
            color: transparent !important;
        }}
        section[data-testid="stSidebar"] .stButton > button:focus {{
            outline: none !important;
            box-shadow: none !important;
        }}
        .block-container {{
            padding-top: 1.25rem;
            padding-bottom: 1.5rem;
        }}
        div[data-testid="stMetric"] {{
            background: white;
            border: 0.5px solid #E2E8F0;
            border-radius: 10px;
            padding: 16px;
        }}
        .rbr-card {{
            background: white;
            border: 0.5px solid #E2E8F0;
            border-radius: 10px;
            padding: 16px;
        }}
        .rbr-chip {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 600;
            background: {AZUL_SUAVE};
            color: {AZUL_MEDIO};
            margin-right: 6px;
            margin-bottom: 6px;
        }}
        .rbr-badge {{
            display: inline-block;
            padding: 5px 10px;
            border-radius: 999px;
            background: {AZUL_SUAVE};
            color: {AZUL_MEDIO};
            font-size: 12px;
            font-weight: 600;
        }}
        div[data-testid="stAppViewContainer"] > section:not([data-testid="stSidebar"]) .stButton > button,
        div[data-testid="stAppViewContainer"] > section:not([data-testid="stSidebar"]) .stDownloadButton > button {{
            background: {AZUL_MEDIO};
            color: white;
            border: 1px solid {AZUL_MEDIO};
            border-radius: 7px;
        }}
        div[data-testid="stAppViewContainer"] > section:not([data-testid="stSidebar"]) .stButton > button[kind="secondary"] {{
            background: white;
            color: {AZUL_MEDIO};
        }}
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"], .stMultiSelect div[data-baseweb="select"] {{
            border-radius: 6px !important;
            background: {CINZA_BG};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar_nav(current_page: str) -> None:
    st.sidebar.markdown(
        """
<div style="padding: 18px 14px 14px; border-bottom: 0.5px solid rgba(255,255,255,0.1); margin-bottom: 4px;">
    <div style="
        width: 34px; height: 34px;
        background: #185FA5;
        border-radius: 8px;
        display: flex; align-items: center; justify-content: center;
        margin-bottom: 8px;
    ">
        <svg width="18" height="18" viewBox="0 0 20 20" fill="white">
            <path d="M2 15 L6 6 L10 11 L13 5 L18 13 Z"/>
        </svg>
    </div>
    <div style="font-size:13px; font-weight:500; color:#ffffff; line-height:1.2;">RBR Logística</div>
    <div style="font-size:10px; color:#85B7EB; margin-top:2px;">Sistema de Fretes</div>
</div>
""",
        unsafe_allow_html=True,
    )

    pages = [
        ("Principal", [
            ("📊", "Dashboard"),
            ("👥", "Parceiros"),
            ("👤", "Clientes"),
            ("⭐", "Simulação"),
            ("🗺️", "Mapa de Rotas"),
        ]),
        ("Documentos", [
            ("📄", "Orçamentos"),
            ("📤", "Upload de Tabelas"),
        ]),
        ("Gestão", [
            ("❌", "Excluir Parceiro"),
        ]),
    ]

    for group_label, items in pages:
        st.sidebar.markdown(
            f'<div style="font-size:9px;color:#378ADD;padding:10px 8px 3px;'
            f'letter-spacing:0.1em;text-transform:uppercase;">{group_label}</div>',
            unsafe_allow_html=True,
        )
        for icon, page_name in items:
            is_active = current_page == page_name
            is_danger = page_name == "Excluir Parceiro"

            if is_active:
                bg = "rgba(55,138,221,0.25)"
                color = "#ffffff"
                weight = "600"
            elif is_danger:
                bg = "transparent"
                color = "#F09595"
                weight = "400"
            else:
                bg = "transparent"
                color = "#85B7EB"
                weight = "400"

            st.sidebar.markdown(
                f"""
<div style="
    background:{bg};
    border-radius:6px;
    margin-bottom:2px;
    padding:8px 10px;
    display:flex;
    align-items:center;
    gap:9px;
    cursor:pointer;
    font-size:12px;
    font-weight:{weight};
    color:{color};
">
    <span>{icon}</span><span>{page_name}</span>
</div>
""",
                unsafe_allow_html=True,
            )
            if st.sidebar.button(
                page_name,
                key=f"nav_{page_name}",
                use_container_width=True,
            ):
                st.session_state["current_page"] = page_name
                st.rerun()
