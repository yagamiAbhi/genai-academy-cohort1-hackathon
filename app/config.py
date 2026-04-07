import logging
import os
from functools import lru_cache

import google.cloud.logging
from dotenv import load_dotenv


# Load environment variables early
load_dotenv()


class Settings:
    model: str = os.getenv("MODEL", "gemini-3.1-pro-preview")
    # BigQuery dataset for persistence (created if missing)
    bigquery_dataset: str = os.getenv("BQ_DATASET", "assistant_data")
    google_cloud_project: str = os.getenv("GOOGLE_CLOUD_PROJECT", "project_not_set")
    maps_api_key: str = os.getenv("MAPS_API_KEY", "")
    bigquery_project: str = os.getenv("BIGQUERY_PROJECT", google_cloud_project)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def setup_logging() -> None:
    """
    Configure Cloud Logging if credentials are available; otherwise fallback to standard logging.
    Mirrors codelab style.
    """
    try:
        client = google.cloud.logging.Client()
        client.setup_logging()
    except Exception:
        logging.basicConfig(
            level=getattr(logging, get_settings().log_level.upper(), logging.INFO),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
