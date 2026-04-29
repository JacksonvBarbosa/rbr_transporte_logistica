from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

from rbr_transporte_logistica.app.pages import simulacao


class FakeColumn:
    def __init__(self, parent=None) -> None:
        self.parent = parent

    def text_input(self, _label: str, value: str = "", max_chars: int | None = None) -> str:
        return value

    def metric(self, *_args, **_kwargs) -> None:
        return None

    def selectbox(self, _label: str, options: list[str], index: int = 0, key: str | None = None) -> str:
        return options[index]

    def button(self, _label: str, *_, key: str | None = None, **_kwargs) -> bool:
        if self.parent is None:
            return False
        if key is not None and key in self.parent.clicked_buttons:
            return True
        return self.parent.submit_value


class FakeForm:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeStreamlit:
    def __init__(
        self,
        session_state: dict,
        *,
        checkbox_value: bool = True,
        submit_value: bool = False,
        clicked_buttons: set[str] | None = None,
    ) -> None:
        self.session_state = session_state
        self.multiselect_calls: list[dict] = []
        self.selectbox_calls: list[dict] = []
        self.error_messages: list[str] = []
        self.checkbox_value = checkbox_value
        self.submit_value = submit_value
        self.clicked_buttons = clicked_buttons or set()

    def header(self, *_args, **_kwargs) -> None:
        return None

    def markdown(self, *_args, **_kwargs) -> None:
        return None

    def caption(self, *_args, **_kwargs) -> None:
        return None

    def form(self, _key: str):
        return FakeForm()

    def columns(self, count):
        size = count if isinstance(count, int) else len(count)
        return [FakeColumn(self) for _ in range(size)]

    def form_submit_button(self, *_args, **_kwargs) -> bool:
        return self.submit_value

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

    def write(self, *_args, **_kwargs) -> None:
        return None

    def success(self, *_args, **_kwargs) -> None:
        return None

    def rerun(self) -> None:
        return None

    def error(self, message: str) -> None:
        self.error_messages.append(message)

    def multiselect(self, label: str, options: list[int], default: list[int], format_func, key: str | None = None):
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
        key = _kwargs.get("key")
        return key in self.clicked_buttons

    def radio(self, _label: str, options: list[str], **_kwargs):
        return options[0]

    def checkbox(self, *_args, **_kwargs) -> bool:
        return self.checkbox_value

    def selectbox(self, label: str, options: list[str], index: int | None = 0, key: str | None = None, **_kwargs):
        self.selectbox_calls.append({"label": label, "options": options, "index": index, "key": key})
        if index is None:
            return None
        return options[index]

    def segmented_control(self, _label: str, options: list[str], format_func=None, default=None):
        if default in options:
            return default
        return options[0]

    def download_button(self, *_args, **_kwargs) -> None:
        return None

    def number_input(self, _label: str, min_value: float = 0.0, value: float = 0.0, step: float = 1.0):
        return value


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

    def simulate(self, **_kwargs):
        raise AssertionError("simulate nao deveria ser chamado neste teste")


def test_render_sanitizes_selected_partner_ids_before_multiselect(monkeypatch):
    partners = [
        SimpleNamespace(id=1, name="Parceiro A", city="Campinas", state="SP", active=True),
        SimpleNamespace(id=3, name="Parceiro C", city="Curitiba", state="PR", active=True),
    ]
    st = FakeStreamlit(
        session_state={
            "last_simulation": {
                "distance_km": 100.0,
                "valid_partner_ids": [1, 3],
                "results": [
                    SimpleNamespace(
                        partner_id=1,
                        partner_name="Parceiro A",
                        city="Campinas",
                        state="SP",
                        distance_km=100.0,
                        price=150.0,
                        deadline_days=2,
                        route_segments=[],
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
    monkeypatch.setattr(simulacao, "apply_theme", lambda: None)
    monkeypatch.setattr(simulacao, "sidebar_nav", lambda _page: None)
    monkeypatch.setattr(simulacao, "db_session", lambda: nullcontext(object()))
    monkeypatch.setattr(simulacao, "build_partner_controller", lambda _session: FakePartnerController(partners))
    monkeypatch.setattr(simulacao, "build_freight_controller", lambda _session: FakeFreightController())
    monkeypatch.setattr(simulacao, "build_cliente_repository", lambda _session: SimpleNamespace(listar=lambda: []))
    monkeypatch.setattr(
        simulacao,
        "build_quote_controller",
        lambda: SimpleNamespace(create_quote=lambda **_kwargs: {}, export_pdf=lambda _data: b"", export_excel=lambda _data: b""),
    )

    simulacao.render()

    assert st.session_state["selected_partner_ids"] == [3]
    assert st.multiselect_calls == [
        {
            "label": "Selecionar parceiros da rota em ordem",
            "options": [1, 3],
            "default": [3],
            "formatted": ["Parceiro A (Campinas/SP)", "Parceiro C (Curitiba/PR)"],
        }
    ]


def test_render_shows_route_error_and_clears_last_route(monkeypatch):
    partners = [SimpleNamespace(id=1, name="Parceiro A", city="Campinas", state="SP", active=True)]

    class FailingFreightController(FakeFreightController):
        def simulate(self, **_kwargs):
            raise ValueError("No valid route found")

    st = FakeStreamlit(
        session_state={"last_route": {"selected_partner_ids": [1]}},
        submit_value=True,
    )

    monkeypatch.setattr(simulacao, "st", st)
    monkeypatch.setattr(simulacao, "apply_theme", lambda: None)
    monkeypatch.setattr(simulacao, "sidebar_nav", lambda _page: None)
    monkeypatch.setattr(simulacao, "db_session", lambda: nullcontext(object()))
    monkeypatch.setattr(simulacao, "build_partner_controller", lambda _session: FakePartnerController(partners))
    monkeypatch.setattr(simulacao, "build_freight_controller", lambda _session: FailingFreightController())
    monkeypatch.setattr(simulacao, "build_cliente_repository", lambda _session: SimpleNamespace(listar=lambda: []))
    monkeypatch.setattr(simulacao, "get_coordinates", lambda city, state: (0.0, 0.0))
    monkeypatch.setattr(
        simulacao,
        "build_quote_controller",
        lambda: SimpleNamespace(create_quote=lambda **_kwargs: {}, export_pdf=lambda _data: b"", export_excel=lambda _data: b""),
    )

    simulacao.render()

    assert st.error_messages == ["No valid route found"]
    assert "last_route" not in st.session_state
