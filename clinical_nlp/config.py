from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Engine settings — all read from RISK_ENGINE_* environment variables."""

    spacy_model: str = "en_core_web_sm"
    negation_pre_window: int = 5
    negation_post_window: int = 3
    severity_window: int = 3
    data_adapter: str = "synthetic"
    synthetic_data_path: str = "data/synthetic/sample_notes.jsonl"

    # Comma-separated list of allowed CORS origins.
    # Use "*" to allow all (development only).
    # Production example: "https://myapp.vercel.app,https://www.myapp.com"
    allowed_origins: str = "http://localhost:8000"

    model_config = {"env_prefix": "RISK_ENGINE_"}


class SupabaseSettings(BaseSettings):
    """
    Supabase connection settings — read from standard SUPABASE_* env vars.
    Field names are intentionally short so the prefix composes correctly:
      env_prefix "SUPABASE_" + field "url"              → SUPABASE_URL
      env_prefix "SUPABASE_" + field "anon_key"         → SUPABASE_ANON_KEY
      env_prefix "SUPABASE_" + field "service_role_key" → SUPABASE_SERVICE_ROLE_KEY

    url              — project URL, safe to expose to the frontend
    anon_key         — public anon key, safe to expose to the frontend
    service_role_key — secret admin key, NEVER sent to the frontend
    """

    url: str = ""
    anon_key: str = ""
    service_role_key: str = ""

    model_config = {"env_prefix": "SUPABASE_", "env_file": ".env"}


settings = Settings()
supabase_settings = SupabaseSettings()
