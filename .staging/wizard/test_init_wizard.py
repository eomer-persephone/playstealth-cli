"""Unit tests for playstealth_actions.init_wizard."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


@pytest.fixture
def fresh_modules(tmp_path, monkeypatch):
    monkeypatch.setenv("PLAYSTEALTH_STATE_DIR", str(tmp_path / "state"))
    from playstealth_actions import persona_manager as pm

    importlib.reload(pm)
    from playstealth_actions import init_wizard as iw

    importlib.reload(iw)
    return iw, pm, tmp_path


class TestEnsureStateDir:
    def test_creates_dir(self, fresh_modules, capsys):
        iw, _, tmp_path = fresh_modules
        result = iw._ensure_state_dir()
        assert result.exists()
        assert result.is_dir()


class TestEnsureDefaultPersona:
    def test_creates_when_missing(self, fresh_modules):
        iw, pm, _ = fresh_modules
        assert not (pm.PERSONA_FILE).exists()
        created = iw._ensure_default_persona()
        assert created is True
        assert pm.PERSONA_FILE.exists()

    def test_skips_when_present(self, fresh_modules):
        iw, pm, _ = fresh_modules
        pm.create_persona("default", age=42)
        created = iw._ensure_default_persona()
        assert created is False


class TestEnsureEnvFile:
    def test_copies_example(self, fresh_modules, tmp_path):
        iw, _, _ = fresh_modules
        (tmp_path / ".env.example").write_text("FOO=bar\n")
        created, msg = iw._ensure_env_file(tmp_path)
        assert created is True
        assert (tmp_path / ".env").read_text() == "FOO=bar\n"

    def test_does_not_overwrite(self, fresh_modules, tmp_path):
        iw, _, _ = fresh_modules
        (tmp_path / ".env.example").write_text("FOO=bar\n")
        (tmp_path / ".env").write_text("EXISTING=value\n")
        created, msg = iw._ensure_env_file(tmp_path)
        assert created is False
        assert (tmp_path / ".env").read_text() == "EXISTING=value\n"

    def test_skips_when_no_example(self, fresh_modules, tmp_path):
        iw, _, _ = fresh_modules
        created, msg = iw._ensure_env_file(tmp_path)
        assert created is False
        assert "no .env.example" in msg


class TestRunInitWizard:
    def test_idempotent_double_run(self, fresh_modules, tmp_path, capsys):
        iw, _, _ = fresh_modules
        (tmp_path / ".env.example").write_text("X=1\n")
        rc1 = iw.run_init_wizard(project_root=tmp_path, non_interactive=True)
        rc2 = iw.run_init_wizard(project_root=tmp_path, non_interactive=True)
        assert rc1 == 0
        assert rc2 == 0

    def test_prints_step_headers(self, fresh_modules, tmp_path, capsys):
        iw, _, _ = fresh_modules
        iw.run_init_wizard(project_root=tmp_path, non_interactive=True)
        out = capsys.readouterr().out
        assert "[1/4]" in out
        assert "[2/4]" in out
        assert "[3/4]" in out
        assert "[4/4]" in out
