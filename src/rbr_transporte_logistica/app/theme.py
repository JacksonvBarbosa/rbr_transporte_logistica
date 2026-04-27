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
        .stAppHeader {{
            display: none;
        }}
        section[data-testid="stSidebar"] {{
            background: {AZUL_ESCURO};
            color: white;
            padding-top: 0.5rem;
        }}
        section[data-testid="stSidebar"] * {{
            color: white;
        }}
        section[data-testid="stSidebar"] .st-emotion-cache-16txtl3,
        section[data-testid="stSidebar"] .st-emotion-cache-1cypcdb {{
            padding-top: 0.5rem;
            padding-bottom: 0.75rem;
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
            display:inline-block;
            padding:4px 10px;
            border-radius:999px;
            font-size:12px;
            font-weight:600;
            background:{AZUL_SUAVE};
            color:{AZUL_MEDIO};
            margin-right:6px;
            margin-bottom:6px;
        }}
        .rbr-badge {{
            display:inline-block;
            padding:5px 10px;
            border-radius:999px;
            background:{AZUL_SUAVE};
            color:{AZUL_MEDIO};
            font-size:12px;
            font-weight:600;
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
        }}
        .rbr-logo {{
            font-size: 24px;
            font-weight: 800;
            color: white;
            margin-bottom: 2px;
        }}
        .rbr-logo-sub {{
            color: #A9C8EA;
            font-size: 13px;
            margin-bottom: 14px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar_nav(current_page: str) -> None:
    with st.sidebar:
        st.markdown('<div class="rbr-logo">RBR Logística</div>', unsafe_allow_html=True)
        st.markdown('<div class="rbr-logo-sub">Operação, simulação e documentos</div>', unsafe_allow_html=True)
        current_section = None
        for section, page in PAGE_ORDER:
            if section != current_section:
                st.markdown(f'<div class="rbr-nav-title">{section}</div>', unsafe_allow_html=True)
                current_section = section
            label = page
            kind = "primary" if page == current_page else "secondary"
            if page == "Excluir Parceiro":
                st.markdown(
                    f"<div style='color:{VERMELHO};font-weight:600;margin:.25rem 0 .15rem 0'>{label}</div>",
                    unsafe_allow_html=True,
                )
            if st.button(label, key=f"nav_{page}", use_container_width=True, type=kind):
                st.session_state["current_page"] = page
                st.rerun()
