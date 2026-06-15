from app.config import load_settings


def test_default_settings_load() -> None:
    settings = load_settings()

    assert settings.default_sport == "football"
    assert settings.default_market == "1X2"
    assert settings.min_edge == 0.07
    assert settings.ai_analysis_mode == "deterministic"
    assert settings.ai_analysis_model_name == "deterministic_ai_fallback"
    assert settings.product_timezone == "Asia/Baku"
    assert settings.misli_result_preview_mode is False
    assert settings.scheduled_settlement_enabled is True
    assert "http://127.0.0.1:5173" in settings.cors_allowed_origins
    assert "railway" in settings.cors_allowed_origin_regex


def test_elo_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("ELO_INITIAL_RATING", "1400")
    monkeypatch.setenv("ELO_K_FACTOR", "32")
    monkeypatch.setenv("ELO_HOME_ADVANTAGE", "80")

    settings = load_settings()

    assert settings.elo_initial_rating == 1400
    assert settings.elo_k_factor == 32
    assert settings.elo_home_advantage == 80


def test_ai_analysis_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("AI_ANALYSIS_MODE", "openai")
    monkeypatch.setenv("AI_ANALYSIS_MODEL_NAME", "gpt-test-analyst")

    settings = load_settings()

    assert settings.ai_analysis_mode == "openai"
    assert settings.ai_analysis_model_name == "gpt-test-analyst"


def test_api_football_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("API_FOOTBALL_KEY", "test-api-football-key")
    monkeypatch.setenv("API_FOOTBALL_BASE_URL", "https://example.test")

    settings = load_settings()

    assert settings.api_football_key == "test-api-football-key"
    assert settings.api_football_base_url == "https://example.test"


def test_sportmonks_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("SPORTMONKS_API_TOKEN", "test-sportmonks-token")
    monkeypatch.setenv("SPORTMONKS_BASE_URL", "https://sportmonks.example.test")

    settings = load_settings()

    assert settings.sportmonks_api_token == "test-sportmonks-token"
    assert settings.sportmonks_base_url == "https://sportmonks.example.test"


def test_product_timezone_loads_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("PRODUCT_TIMEZONE", "UTC")

    settings = load_settings()

    assert settings.product_timezone == "UTC"


def test_cors_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://dashboard.example.com, https://preview.example.com",
    )
    monkeypatch.setenv("CORS_ALLOWED_ORIGIN_REGEX", r"^https://.*\.example\.com$")

    settings = load_settings()

    assert settings.cors_allowed_origins == (
        "https://dashboard.example.com",
        "https://preview.example.com",
    )
    assert settings.cors_allowed_origin_regex == r"^https://.*\.example\.com$"
