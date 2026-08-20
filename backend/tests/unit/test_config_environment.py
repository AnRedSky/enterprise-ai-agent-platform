from pathlib import Path

from app.core.config import BACKEND_ROOT, _env_files


def test_env_files_use_env_example_as_lowest_precedence(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENV_FILE", raising=False)

    paths = _env_files()

    assert paths[0] == str(BACKEND_ROOT / ".env.example")
    assert paths[1] == str(BACKEND_ROOT / ".env")
    assert paths[-2].endswith(".env.development")
    assert paths[-1].endswith(".env.development.local")


def test_env_files_select_requested_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.delenv("ENV_FILE", raising=False)

    paths = _env_files()

    assert paths[0].endswith(".env.example")
    assert paths[-2].endswith(".env.test")
    assert paths[-1].endswith(".env.test.local")


def test_explicit_env_file_has_highest_file_precedence(monkeypatch):
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("ENV_FILE", "/run/secrets/agent.env")

    paths = _env_files()

    assert paths[0].endswith(".env.example")
    assert paths[-1] == "/run/secrets/agent.env"


def test_env_example_exists_for_fresh_checkout():
    assert Path(BACKEND_ROOT / ".env.example").is_file()
