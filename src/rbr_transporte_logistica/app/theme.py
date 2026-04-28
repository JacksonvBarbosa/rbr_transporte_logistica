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

PAGE_ORDER = [
    ("Principal", "Dashboard"),
    ("Principal", "Parceiros"),
    ("Principal", "Simulação"),
    ("Principal", "Mapa de Rotas"),
    ("Documentos", "Orçamentos"),
    ("Documentos", "Upload de Tabelas"),
    ("Gestão", "Excluir Parceiro"),
]


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
        header[data-testid="stHeader"] {{
            display: none !important;
        }}
        [data-testid="collapsedControl"] {{
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            color: {AZUL_MEDIO} !important;
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
        section[data-testid="stSidebar"] .stButton > button {{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #85B7EB !important;
            text-align: left !important;
            width: 100% !important;
            padding: 8px 10px !important;
            border-radius: 6px !important;
            font-size: 12px !important;
            font-weight: 400 !important;
        }}
        section[data-testid="stSidebar"] .stButton > button:hover {{
            background: rgba(55,138,221,0.15) !important;
            color: #ffffff !important;
        }}
        section[data-testid="stSidebar"] .stButton > button[data-active="true"],
        section[data-testid="stSidebar"] .nav-active button {{
            background: rgba(55,138,221,0.22) !important;
            color: #ffffff !important;
            font-weight: 500 !important;
        }}
        section[data-testid="stSidebar"] .nav-danger button {{
            color: #F09595 !important;
        }}
        section[data-testid="stSidebar"] .nav-danger button:hover {{
            background: rgba(242,117,117,0.12) !important;
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
        .stButton > button, .stDownloadButton > button {{
            background: {AZUL_MEDIO};
            color: white;
            border: 1px solid {AZUL_MEDIO};
            border-radius: 7px;
        }}
        .stButton > button[kind="secondary"] {{
            background: white;
            color: {AZUL_MEDIO};
        }}
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"], .stMultiSelect div[data-baseweb="select"] {{
            border-radius: 6px !important;
            background: {CINZA_BG};
        }}
        .rbr-nav-title {{
            color: #A9C8EA;
            font-size: 12px;
            letter-spacing: .08em;
            text-transform: uppercase;
            margin-top: 10px;
            margin-bottom: 4px;
            font-weight: 700;
            padding: 0 10px;
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

    with st.sidebar:
        current_section = None
        for section, page in PAGE_ORDER:
            if section != current_section:
                st.markdown(f'<div class="rbr-nav-title">{section}</div>', unsafe_allow_html=True)
                current_section = section

            wrapper_classes: list[str] = []
            if page == current_page:
                wrapper_classes.append("nav-active")
            if page == "Excluir Parceiro":
                wrapper_classes.append("nav-danger")

            if wrapper_classes:
                st.markdown(
                    f"<div class=\"{' '.join(wrapper_classes)}\">",
                    unsafe_allow_html=True,
                )
            if st.button(page, key=f"nav_{page}", use_container_width=True):
                st.session_state["current_page"] = page
                st.rerun()
            if wrapper_classes:
                st.markdown("</div>", unsafe_allow_html=True)
