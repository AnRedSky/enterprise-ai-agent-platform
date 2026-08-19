from app.core.config import _env_files


def test_env_files_use_development_by_default(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENV_FILE", raising=False)

    paths = _env_files()

    assert paths[-2].endswith(".env.development")
    assert paths[-1].endswith(".env.development.local")


def test_env_files_select_requested_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.delenv("ENV_FILE", raising=False)

    paths = _env_files()

    assert paths[-2].endswith(".env.test")
    assert paths[-1].endswith(".env.test.local")


def test_explicit_env_file_has_highest_file_precedence(monkeypatch):
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("ENV_FILE", "/run/secrets/agent.env")

    paths = _env_files()

    assert paths[-1] == "/run/secrets/agent.env"
