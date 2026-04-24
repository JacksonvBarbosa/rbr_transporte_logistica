from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

from rbr_transporte_logistica.app.pages import simulacao


class FakeColumn:
    def text_input(self, _label: str, value: str = "", max_chars: int | None = None) -> str:
        return value

    def metric(self, *_args, **_kwargs) -> None:
        return None


class FakeForm:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeStreamlit:
    def __init__(self, session_state: dict) -> None:
        self.session_state = session_state
        self.multiselect_calls: list[dict] = []

    def header(self, *_args, **_kwargs) -> None:
        return None

    def caption(self, *_args, **_kwargs) -> None:
        return None

    def form(self, _key: str):
        return FakeForm()

    def columns(self, count: int):
        return [FakeColumn() for _ in range(count)]

    def form_submit_button(self, *_args, **_kwargs) -> bool:
        return False

    def metric(self, *_args, **_kwargs) -> None:
        return None

    def subheader(self, *_args, **_kwargs) -> None:
        return None

    def dataframe(self, *_args, **_kwargs) -> None:
        return None

    def warning(self, *_args, **_kwargs) -> None:
        return None

    def info(self, *_args, **_kwargs) -> None:
        return None

    def error(self, message: str) -> None:
        raise AssertionError(f"Erro inesperado na pagina: {message}")

    def multiselect(self, label: str, options: list[int], default: list[int], format_func):
        self.multiselect_calls.append(
            {
                "label": label,
                "options": options,
                "default": default,
                "formatted": [format_func(option) for option in options],
            }
        )
        return default

    def button(self, *_args, **_kwargs) -> bool:
        return False


class FakePartnerController:
    def __init__(self, partners: list[SimpleNamespace]) -> None:
        self.partners = partners

    def list_partners(self, active_only: bool = False):
        if active_only:
            return [partner for partner in self.partners if partner.active]
        return self.partners


class FakeFreightController:
    def simulate_multi_leg(self, **_kwargs):
        raise AssertionError("simulate_multi_leg nao deveria ser chamado neste teste")


def test_render_sanitizes_selected_partner_ids_before_multiselect(monkeypatch):
    partners = [
        SimpleNamespace(id=1, name="Parceiro A", city="Campinas", state="SP", active=True),
        SimpleNamespace(id=3, name="Parceiro C", city="Curitiba", state="PR", active=True),
    ]
    st = FakeStreamlit(
        session_state={
            "last_simulation": {
                "distance_km": 100.0,
                "results": [
                    SimpleNamespace(
                        partner_id=1,
                        partner_name="Parceiro A",
                        city="Campinas",
                        state="SP",
                        distance_km=100.0,
                        price=150.0,
                        deadline_days=2,
                        rule_type="FIXED",
                    )
                ],
                "best_price": SimpleNamespace(
                    partner_id=1, partner_name="Parceiro A", price=150.0
                ),
                "best_deadline": SimpleNamespace(
                    partner_id=1, partner_name="Parceiro A", deadline_days=2
                ),
                "origin": SimpleNamespace(city="Sao Paulo", state="SP"),
                "destination": SimpleNamespace(city="Campinas", state="SP"),
            },
            "selected_partner_ids": [999, 3],
        }
    )

    monkeypatch.setattr(simulacao, "st", st)
    monkeypatch.setattr(simulacao, "db_session", lambda: nullcontext(object()))
    monkeypatch.setattr(simulacao, "build_partner_controller", lambda _session: FakePartnerController(partners))
    monkeypatch.setattr(simulacao, "build_freight_controller", lambda _session: FakeFreightController())

    simulacao.render()

    assert st.session_state["selected_partner_ids"] == [3]
    assert st.multiselect_calls == [
        {
            "label": "Parceiros da rota, em ordem",
            "options": [1, 3],
            "default": [3],
            "formatted": ["Parceiro A (Campinas/SP)", "Parceiro C (Curitiba/PR)"],
        }
    ]
