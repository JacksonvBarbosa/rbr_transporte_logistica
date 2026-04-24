from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

from rbr_transporte_logistica.app.pages import parceiro_exclusao


class FakeStreamlit:
    def __init__(
        self,
        *,
        session_state: dict | None = None,
        selected_label: str | None = None,
        text_values: dict[str, str] | None = None,
        clicked_buttons: set[str] | None = None,
    ) -> None:
        self.session_state = session_state or {}
        self.selected_label = selected_label
        self.text_values = text_values or {}
        self.clicked_buttons = clicked_buttons or set()
        self.button_calls: list[dict] = []
        self.rerun_called = False
        self.success_messages: list[str] = []
        self.warning_messages: list[str] = []

    def header(self, *_args, **_kwargs) -> None:
        return None

    def caption(self, *_args, **_kwargs) -> None:
        return None

    def info(self, *_args, **_kwargs) -> None:
        return None

    def write(self, *_args, **_kwargs) -> None:
        return None

    def error(self, message: str) -> None:
        raise AssertionError(f"Erro inesperado na pagina: {message}")

    def warning(self, message: str) -> None:
        self.warning_messages.append(message)

    def success(self, message: str) -> None:
        self.success_messages.append(message)

    def selectbox(self, _label: str, options: list[str], key: str | None = None):
        return self.selected_label or options[0]

    def text_input(self, _label: str, key: str | None = None) -> str:
        return self.text_values.get(key or "", "")

    def button(
        self,
        label: str,
        *,
        type: str | None = None,
        key: str | None = None,
        disabled: bool = False,
    ) -> bool:
        self.button_calls.append(
            {"label": label, "type": type, "key": key, "disabled": disabled}
        )
        return not disabled and key in self.clicked_buttons

    def rerun(self) -> None:
        self.rerun_called = True


class FakeSession:
    def __init__(self) -> None:
        self.commit_called = False

    def commit(self) -> None:
        self.commit_called = True


class FakeController:
    def __init__(self, partners: list[SimpleNamespace]) -> None:
        self.partners = partners
        self.deleted_partner_ids: list[int] = []

    def list_partners(self):
        return self.partners

    def delete_partner(self, partner_id: int) -> None:
        self.deleted_partner_ids.append(partner_id)


def _build_partner(*, partner_id: int = 1, name: str = "Parceiro Azul", active: bool = True):
    return SimpleNamespace(
        id=partner_id,
        name=name,
        city="Campinas",
        state="SP",
        active=active,
        freight_rules=[SimpleNamespace(id=10), SimpleNamespace(id=11)],
    )


def test_render_deletes_partner_when_confirmation_matches(monkeypatch):
    partner = _build_partner()
    controller = FakeController([partner])
    session = FakeSession()
    st = FakeStreamlit(
        session_state={"selected_partner_ids": [1, 2]},
        text_values={f"delete_partner_confirmation_{partner.id}": partner.name},
        clicked_buttons={f"confirm_partner_delete_{partner.id}"},
    )

    monkeypatch.setattr(parceiro_exclusao, "st", st)
    monkeypatch.setattr(parceiro_exclusao, "db_session", lambda: nullcontext(session))
    monkeypatch.setattr(parceiro_exclusao, "build_partner_controller", lambda _session: controller)

    parceiro_exclusao.render()

    assert controller.deleted_partner_ids == [partner.id]
    assert session.commit_called is True
    assert "selected_partner_ids" not in st.session_state
    assert st.rerun_called is True
    assert st.success_messages == ["Parceiro excluido com sucesso."]


def test_render_keeps_button_disabled_when_confirmation_does_not_match(monkeypatch):
    partner = _build_partner()
    controller = FakeController([partner])
    session = FakeSession()
    st = FakeStreamlit(
        text_values={f"delete_partner_confirmation_{partner.id}": "Nome incorreto"},
        clicked_buttons={f"confirm_partner_delete_{partner.id}"},
    )

    monkeypatch.setattr(parceiro_exclusao, "st", st)
    monkeypatch.setattr(parceiro_exclusao, "db_session", lambda: nullcontext(session))
    monkeypatch.setattr(parceiro_exclusao, "build_partner_controller", lambda _session: controller)

    parceiro_exclusao.render()

    assert controller.deleted_partner_ids == []
    assert session.commit_called is False
    assert st.rerun_called is False
    assert st.button_calls[-1]["disabled"] is True


def test_render_clears_selected_partner_ids_after_successful_deletion(monkeypatch):
    partner = _build_partner(partner_id=7, name="Parceiro Laranja", active=False)
    controller = FakeController([partner])
    session = FakeSession()
    st = FakeStreamlit(
        session_state={"selected_partner_ids": [7]},
        text_values={f"delete_partner_confirmation_{partner.id}": partner.name},
        clicked_buttons={f"confirm_partner_delete_{partner.id}"},
    )

    monkeypatch.setattr(parceiro_exclusao, "st", st)
    monkeypatch.setattr(parceiro_exclusao, "db_session", lambda: nullcontext(session))
    monkeypatch.setattr(parceiro_exclusao, "build_partner_controller", lambda _session: controller)

    parceiro_exclusao.render()

    assert st.session_state == {}
    assert st.warning_messages == [
        "A exclusao e irreversivel e tambem remove todas as regras de frete vinculadas."
    ]
