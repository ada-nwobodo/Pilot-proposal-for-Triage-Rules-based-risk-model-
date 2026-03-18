from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    spacy_model: str = "en_core_web_sm"
    negation_pre_window: int = 5
    negation_post_window: int = 3
    severity_window: int = 3
    data_adapter: str = "synthetic"
    synthetic_data_path: str = "data/synthetic/sample_notes.jsonl"

    model_config = {"env_prefix": "RISK_ENGINE_"}


settings = Settings()
