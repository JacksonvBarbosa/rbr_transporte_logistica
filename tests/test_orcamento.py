from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from rbr_transporte_logistica.app.pages import orcamento


def _mock_cotacao():
    item = SimpleNamespace(
        origin_label="Origem",
        destination_label="Destino",
        partner_name="Parceiro Azul",
        distance_km=120.0,
        value=350.0,
        deadline_days=3,
        rule_type="FIXED",
        pickup_mode="DIRECT",
    )
    return SimpleNamespace(
        id=1,
        number="COT-00001",
        customer_name="Cliente Teste",
        created_at=datetime(2026, 4, 27, 10, 0, 0),
        origin="Sao Paulo/SP",
        destination="Campinas/SP",
        route_label="Origem -> Destino",
        freight_gross=350.0,
        icms_value=42.0,
        iss_value=17.5,
        margin_value=52.5,
        total_value=462.0,
        total_deadline_days=3,
        direct_distance_km=100.0,
        route_distance_km=120.0,
        icms_rate=0.12,
        iss_rate=0.05,
        margin_rate=0.15,
        items=[item],
    )


def test_gerar_proposta_pdf_sem_erro(tmp_path):
    cotacao = _mock_cotacao()

    pdf_path = orcamento.gerar_proposta_pdf(cotacao, tmp_path)

    assert pdf_path.exists()
    assert pdf_path.suffix == ".pdf"
    assert pdf_path.read_bytes().startswith(b"%PDF")


def test_gerar_relatorio_excel_sem_erro(tmp_path):
    cotacao = _mock_cotacao()

    excel_path = orcamento.gerar_relatorio_excel(cotacao, tmp_path)

    assert excel_path.exists()
    assert excel_path.suffix == ".xlsx"
    assert len(excel_path.read_bytes()) > 0
