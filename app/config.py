from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    database_url: str
    default_sport: str
    default_market: str
    default_stake_units: float
    min_edge: float
    min_odds: float
    max_odds: float
    feature_version: str
    model_name: str
    model_version: str
    elo_initial_rating: float
    elo_k_factor: float
    elo_home_advantage: float
    log_level: str
    live_collection_enabled: bool
    ai_analysis_mode: str = "deterministic"
    ai_analysis_model_name: str = "deterministic_ai_fallback"
    cors_allowed_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )
    cors_allowed_origin_regex: str = (
        r"^(http://(localhost|127\.0\.0\.1):\d+|https://[a-z0-9-]+\.up\.railway\.app)$"
    )


def _get_float(name: str, default: str) -> float:
    value = getenv(name, default)
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {value!r}") from exc


def _get_bool(name: str, default: str) -> bool:
    return getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _get_csv(name: str, default: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in getenv(name, default).split(",") if part.strip())


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        database_url=getenv("DATABASE_URL", "sqlite:///data/paper_odds_lab.sqlite"),
        default_sport=getenv("DEFAULT_SPORT", "football"),
        default_market=getenv("DEFAULT_MARKET", "1X2"),
        default_stake_units=_get_float("DEFAULT_STAKE_UNITS", "1.0"),
        min_edge=_get_float("MIN_EDGE", "0.07"),
        min_odds=_get_float("MIN_ODDS", "1.70"),
        max_odds=_get_float("MAX_ODDS", "3.50"),
        feature_version=getenv("FEATURE_VERSION", "v0_baseline"),
        model_name=getenv("MODEL_NAME", "baseline_heuristic"),
        model_version=getenv("MODEL_VERSION", "v0"),
        elo_initial_rating=_get_float("ELO_INITIAL_RATING", "1500"),
        elo_k_factor=_get_float("ELO_K_FACTOR", "20"),
        elo_home_advantage=_get_float("ELO_HOME_ADVANTAGE", "65"),
        log_level=getenv("LOG_LEVEL", "INFO"),
        live_collection_enabled=_get_bool("LIVE_COLLECTION_ENABLED", "false"),
        ai_analysis_mode=getenv("AI_ANALYSIS_MODE", "deterministic"),
        ai_analysis_model_name=getenv("AI_ANALYSIS_MODEL_NAME", "deterministic_ai_fallback"),
        cors_allowed_origins=_get_csv(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ),
        cors_allowed_origin_regex=getenv(
            "CORS_ALLOWED_ORIGIN_REGEX",
            r"^(http://(localhost|127\.0\.0\.1):\d+|https://[a-z0-9-]+\.up\.railway\.app)$",
        ),
    )
