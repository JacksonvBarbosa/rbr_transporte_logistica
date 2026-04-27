from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from rbr_transporte_logistica.app.theme import (
    AMBAR,
    AZUL_CLARO,
    ROXO,
    TEAL,
    apply_theme,
    sidebar_nav,
)
from rbr_transporte_logistica.core.database import db_session
from rbr_transporte_logistica.repositories.quote_repository import CotacaoRepo, ParceiroRepo

try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except Exception:  # pragma: no cover
    px = None
    go = None
    make_subplots = None


def render() -> None:
    apply_theme()
    sidebar_nav("Dashboard")
    st.markdown(
        "### Dashboard - analise de negocio "
        "<span class='rbr-badge'>Ultimos 30 dias</span>",
        unsafe_allow_html=True,
    )

    with db_session() as session:
        cotacao_repo = CotacaoRepo(session)
        parceiro_repo = ParceiroRepo(session)
        closed_quotes = cotacao_repo.listar_fechadas()
        recent_quotes = cotacao_repo.listar_recentes(20)
        parceiros_ativos = parceiro_repo.contar_ativos()

    faturamento = sum(float(quote.total_value) for quote in closed_quotes)
    fretes_fechados = len(closed_quotes)
    ticket_medio = faturamento / fretes_fechados if fretes_fechados else 0.0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Faturamento estimado", f"R$ {faturamento:,.2f}")
    col2.metric("Fretes fechados", f"{fretes_fechados}")
    col3.metric("Ticket medio", f"R$ {ticket_medio:,.2f}")
    col4.metric("Parceiros ativos", f"{parceiros_ativos}")

    monthly_rows = _build_monthly_metrics(closed_quotes)
    st.markdown("#### Evolucao de fretes fechados - ultimos 6 meses")
    if make_subplots and go:
        figure = make_subplots(specs=[[{"secondary_y": True}]])
        figure.add_bar(
            x=monthly_rows["mes"],
            y=monthly_rows["quantidade"],
            name="Quantidade",
            marker_color=AZUL_CLARO,
        )
        figure.add_trace(
            go.Scatter(
                x=monthly_rows["mes"],
                y=monthly_rows["valor_total"],
                name="Valor",
                line={"color": TEAL, "width": 3},
            ),
            secondary_y=True,
        )
        figure.update_layout(
            height=340,
            margin={"l": 10, "r": 10, "t": 10, "b": 10},
            showlegend=True,
        )
        st.plotly_chart(figure, use_container_width=True)
    else:
        st.line_chart(
            monthly_rows.set_index("mes")[["quantidade", "valor_total"]],
            use_container_width=True,
        )

    donut_col, bar_col, spark_col = st.columns(3)
    with donut_col:
        st.markdown("#### Fretes por tipo de regra")
        rule_df = _build_rule_type_df(closed_quotes)
        if px and not rule_df.empty:
            fig = px.pie(
                rule_df,
                names="tipo",
                values="quantidade",
                hole=0.55,
                color="tipo",
                color_discrete_map={
                    "LINEAR": AZUL_CLARO,
                    "TIERED": ROXO,
                    "FIXED": AMBAR,
                },
            )
            fig.update_layout(height=280, margin={"l": 10, "r": 10, "t": 10, "b": 10})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.dataframe(rule_df, hide_index=True, use_container_width=True)

    with bar_col:
        st.markdown("#### Top 5 parceiros por volume R$")
        partner_df = _build_partner_volume_df(closed_quotes)
        if px and not partner_df.empty:
            fig = px.bar(
                partner_df,
                x="valor",
                y="parceiro",
                orientation="h",
                color_discrete_sequence=[AZUL_CLARO],
            )
            fig.update_layout(
                height=280,
                margin={"l": 10, "r": 10, "t": 10, "b": 10},
                yaxis={"categoryorder": "total ascending"},
                xaxis_showgrid=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.dataframe(partner_df, hide_index=True, use_container_width=True)

    with spark_col:
        st.markdown("#### Distancia media das rotas")
        avg_distance, spark_df = _build_distance_trend_df(closed_quotes)
        st.metric("Distancia media", f"{avg_distance:,.1f} km")
        if go and not spark_df.empty:
            fig = go.Figure(
                go.Scatter(
                    x=spark_df["data"],
                    y=spark_df["distancia"],
                    line={"color": TEAL, "width": 3},
                    fill="tozeroy",
                )
            )
            fig.update_layout(
                height=220,
                margin={"l": 10, "r": 10, "t": 10, "b": 10},
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.line_chart(
                spark_df.set_index("data")[["distancia"]] if not spark_df.empty else pd.DataFrame(),
                use_container_width=True,
            )

    st.markdown("#### Fretes recentes")
    recent_df = pd.DataFrame(
        [
            {
                "Nº": quote.number,
                "Cliente": quote.customer_name,
                "Rota": quote.route_label,
                "Parceiro": quote.partner_name,
                "Valor": float(quote.total_value),
                "Prazo": int(quote.total_deadline_days),
                "Status": quote.status,
            }
            for quote in recent_quotes
        ]
    )
    st.dataframe(recent_df, hide_index=True, use_container_width=True)


def _build_monthly_metrics(quotes: list) -> pd.DataFrame:
    now = datetime.utcnow()
    month_starts = []
    current = now.replace(day=1)
    for _ in range(6):
        month_starts.append(current)
        current = (current - timedelta(days=1)).replace(day=1)
    grouped: dict[str, dict[str, float]] = {
        month.strftime("%b/%y"): {"quantidade": 0, "valor_total": 0.0}
        for month in reversed(month_starts)
    }
    for quote in quotes:
        label = quote.created_at.strftime("%b/%y")
        if label in grouped:
            grouped[label]["quantidade"] += 1
            grouped[label]["valor_total"] += float(quote.total_value)
    return pd.DataFrame([{"mes": label, **payload} for label, payload in grouped.items()])


def _build_rule_type_df(quotes: list) -> pd.DataFrame:
    totals: dict[str, int] = defaultdict(int)
    for quote in quotes:
        for item in quote.items:
            totals[item.rule_type] += 1
    return pd.DataFrame([{"tipo": key, "quantidade": value} for key, value in totals.items()])


def _build_partner_volume_df(quotes: list) -> pd.DataFrame:
    totals: dict[str, float] = defaultdict(float)
    for quote in quotes:
        for item in quote.items:
            totals[item.partner_name] += float(item.value)
    rows = sorted(
        ({"parceiro": key, "valor": value} for key, value in totals.items()),
        key=lambda row: row["valor"],
        reverse=True,
    )[:5]
    return pd.DataFrame(rows)


def _build_distance_trend_df(quotes: list) -> tuple[float, pd.DataFrame]:
    rows = [
        {"data": quote.created_at.date(), "distancia": float(quote.route_distance_km)}
        for quote in quotes[:12]
    ]
    df = pd.DataFrame(rows)
    if df.empty:
        return 0.0, pd.DataFrame(columns=["data", "distancia"])
    return float(df["distancia"].mean()), df.sort_values("data")
