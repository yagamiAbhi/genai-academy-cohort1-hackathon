from datetime import datetime
from typing import Dict

from google.cloud import bigquery

from app.config import get_settings

settings = get_settings()

DATASET = settings.bigquery_dataset
PROJECT = settings.bigquery_project


def get_bq_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT)


def ensure_tables() -> None:
    """Create dataset and tables if they don't exist."""
    client = get_bq_client()

    dataset_ref = bigquery.Dataset(f"{PROJECT}.{DATASET}")
    dataset_ref.location = "US"
    try:
        client.get_dataset(dataset_ref)
    except Exception:
        client.create_dataset(dataset_ref, exists_ok=True)

    tables: Dict[str, str] = {
        "tasks": """
            CREATE TABLE IF NOT EXISTS `{project}.{dataset}.tasks` (
              id INT64,
              title STRING NOT NULL,
              due TIMESTAMP,
              status STRING,
              notes STRING,
              created_at TIMESTAMP,
              updated_at TIMESTAMP
            )
        """,
        "events": """
            CREATE TABLE IF NOT EXISTS `{project}.{dataset}.events` (
              id INT64,
              title STRING NOT NULL,
              start TIMESTAMP,
              end TIMESTAMP,
              location STRING,
              description STRING,
              created_at TIMESTAMP,
              updated_at TIMESTAMP
            )
        """,
        "notes": """
            CREATE TABLE IF NOT EXISTS `{project}.{dataset}.notes` (
              id INT64,
              title STRING NOT NULL,
              content STRING,
              created_at TIMESTAMP,
              updated_at TIMESTAMP
            )
        """,
    }

    for ddl in tables.values():
        client.query(
            ddl.format(project=PROJECT, dataset=DATASET)
        ).result()
