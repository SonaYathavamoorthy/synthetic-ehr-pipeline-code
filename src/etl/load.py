"""
Load: create the warehouse schema and bulk-load transformed DataFrames.
"""
import logging
import sqlite3
import pandas as pd
from .config import DB_PATH, SCHEMA_PATH

log = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    log.info("Schema created from sql/schema.sql")


def load_table(conn: sqlite3.Connection, df: pd.DataFrame, table_name: str, chunksize: int = 5000) -> None:
    df.to_sql(table_name, conn, if_exists="append", index=False, chunksize=chunksize)
    log.info(f"Loaded {len(df):,} rows into {table_name}")
