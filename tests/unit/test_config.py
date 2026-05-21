from app.config import load_settings


def test_default_settings_load() -> None:
    settings = load_settings()

    assert settings.default_sport == "football"
    assert settings.default_market == "1X2"
    assert settings.min_edge == 0.07
    assert settings.ai_analysis_mode == "deterministic"
    assert settings.ai_analysis_model_name == "deterministic_ai_fallback"


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
