from __future__ import annotations

from dataclasses import asdict, is_dataclass
from io import BytesIO
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_quote_pdf(summary, items: Iterable) -> bytes:
    summary_payload = asdict(summary) if is_dataclass(summary) else dict(summary)
    rows = list(items)

    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    elements = [Paragraph("Orcamento de Frete", styles["Title"]), Spacer(1, 12)]
    elements.append(
        Paragraph(
            (
                f"Origem: {summary_payload['origin']} | Destino: {summary_payload['destination']} | "
                f"Distancia direta: {summary_payload['direct_distance_km']} km | "
                f"Rota total: {summary_payload['route_distance_km']} km"
            ),
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 12))

    table_data = [["Trecho", "Partner", "Distancia", "Preco", "Prazo", "Regra"]]
    for row in rows:
        table_data.append(
            [
                f"{row.origin_label} -> {row.destination_label}",
                row.partner_name,
                f"{row.distance_km:,.2f} km",
                f"R$ {row.price:,.2f}",
                f"{row.deadline_days} dias",
                row.rule_type,
            ]
        )

    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b5394")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
            ]
        )
    )
    elements.extend([table, Spacer(1, 16)])

    elements.append(Paragraph(f"Subtotal: R$ {summary_payload['subtotal']:,.2f}", styles["Normal"]))
    elements.append(Paragraph(f"Taxes: R$ {summary_payload['taxes']:,.2f}", styles["Normal"]))
    elements.append(Paragraph(f"Margin: R$ {summary_payload['margin']:,.2f}", styles["Normal"]))
    elements.append(
        Paragraph(
            f"Additional Fees: R$ {summary_payload['additional_fees']:,.2f}",
            styles["Normal"],
        )
    )
    elements.append(
        Paragraph(
            f"Prazo total estimado: {summary_payload['total_deadline_days']} dias",
            styles["Normal"],
        )
    )
    elements.append(Paragraph(f"Final Total: R$ {summary_payload['total']:,.2f}", styles["Heading2"]))

    document.build(elements)
    buffer.seek(0)
    return buffer.read()
