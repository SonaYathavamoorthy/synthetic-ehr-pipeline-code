"""Central config: paths used across the ETL pipeline."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DB_PATH = PROCESSED_DIR / "ehr_warehouse.db"
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
