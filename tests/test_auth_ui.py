"""Exercise the actual sidebar with a synthetic adapter; no live DB or browser."""
from contextlib import nullcontext
from types import SimpleNamespace

import auth


class Sidebar:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            if name == "form":
                return nullcontext()
            return False
        return call


def test_anonymous_form_is_blank_and_has_no_account_selector(session, monkeypatch):
    sidebar = Sidebar()
    inputs = []
    def text_input(label, **kwargs):
        inputs.append((label, kwargs))
        return ""
    monkeypatch.setattr(auth, "st", SimpleNamespace(session_state=session, sidebar=sidebar,
                       text_input=text_input, form_submit_button=lambda *a, **k: False))
    auth.render_auth_sidebar()
    assert len(inputs) == 2
    assert all(not kwargs.get("value") for _, kwargs in inputs)
    assert inputs[1][1]["type"] == "password"
    assert not any(name in ("selectbox", "radio") for name, _, _ in sidebar.calls)


def test_authenticated_sidebar_has_no_identity_switch(session, sign_in, monkeypatch):
    sign_in("staff")
    sidebar = Sidebar()
    monkeypatch.setattr(auth, "st", SimpleNamespace(session_state=session, sidebar=sidebar))
    auth.render_auth_sidebar()
    assert not any(name in ("selectbox", "radio") for name, _, _ in sidebar.calls)
    assert session.user_info['id'] == 3


def test_query_parameters_cannot_set_identity(session, sign_in, monkeypatch):
    sign_in("staff")
    monkeypatch.setattr(auth.st, "query_params", {"user_id": "1", "role": "admin"}, raising=False)
    assert auth.get_authenticated_user()["id"] == 3
    assert session.role == "employee"
