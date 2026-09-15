"""
Orchestrates the full ETL run: extract -> transform -> load -> validate.

Usage:
    python -m src.etl.run_pipeline
"""
import logging
import sys
import time

from . import extract, transform, load
from .config import DB_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)


def run_quality_checks(conn) -> bool:
    """
    Lightweight data quality gate, run after every load:
      - primary keys are unique / not null
      - fact tables don't reference patient_ids missing from dim_patient
      - no fully-null critical columns
    Returns True if all checks pass; logs and returns False otherwise.
    """
    checks_passed = True
    cur = conn.cursor()

    # 1. Uniqueness of dimension primary keys
    for table, key in [("dim_patient", "patient_id"), ("dim_provider", "provider_id"),
                        ("dim_organization", "organization_id")]:
        cur.execute(f"SELECT COUNT(*), COUNT(DISTINCT {key}) FROM {table}")
        total, distinct = cur.fetchone()
        if total != distinct:
            log.error(f"QUALITY CHECK FAILED: {table}.{key} has {total - distinct} duplicate keys")
            checks_passed = False
        else:
            log.info(f"QUALITY CHECK OK: {table}.{key} is unique ({distinct:,} rows)")

    # 2. Referential integrity: fact rows pointing to a patient_id not in dim_patient
    for table in ["fact_encounters", "fact_conditions", "fact_medications",
                   "fact_procedures", "fact_observations"]:
        cur.execute(f"""
            SELECT COUNT(*) FROM {table} f
            LEFT JOIN dim_patient p ON f.patient_id = p.patient_id
            WHERE p.patient_id IS NULL
        """)
        orphans = cur.fetchone()[0]
        if orphans > 0:
            log.error(f"QUALITY CHECK FAILED: {table} has {orphans} rows with an unknown patient_id")
            checks_passed = False
        else:
            log.info(f"QUALITY CHECK OK: {table} — no orphaned patient_id references")

    # 3. Null checks on columns that should always be populated
    critical_cols = {
        "dim_patient": ["patient_id", "birthdate", "gender"],
        "fact_encounters": ["encounter_id", "patient_id", "encounter_class"],
    }
    for table, cols in critical_cols.items():
        for col in cols:
            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL")
            nulls = cur.fetchone()[0]
            if nulls > 0:
                log.error(f"QUALITY CHECK FAILED: {table}.{col} has {nulls} NULL values")
                checks_passed = False

    return checks_passed


def main():
    start = time.time()
    log.info("=== Starting Synthetic EHR ETL pipeline ===")

    # remove any previous DB so re-runs are idempotent
    if DB_PATH.exists():
        DB_PATH.unlink()
        log.info(f"Removed existing warehouse at {DB_PATH}")

    # --- EXTRACT ---
    raw = extract.extract_all()

    # --- TRANSFORM ---
    dim_patient = transform.build_dim_patient(raw["patients"])
    dim_organization = transform.build_dim_organization(raw["organizations"])
    dim_provider = transform.build_dim_provider(raw["providers"])

    fact_encounters = transform.build_fact_encounters(raw["encounters"])
    fact_conditions = transform.build_fact_conditions(raw["conditions"])
    fact_medications = transform.build_fact_medications(raw["medications"])
    fact_procedures = transform.build_fact_procedures(raw["procedures"])
    fact_observations = transform.build_fact_observations(raw["observations"])

    dim_date = transform.build_dim_date(
        fact_encounters["start_date_key"], fact_conditions["start_date_key"],
        fact_medications["start_date_key"], fact_procedures["date_key"],
        fact_observations["date_key"],
    )

    # --- LOAD ---
    conn = load.get_connection()
    load.create_schema(conn)

    load.load_table(conn, dim_date, "dim_date")
    load.load_table(conn, dim_patient, "dim_patient")
    load.load_table(conn, dim_organization, "dim_organization")
    load.load_table(conn, dim_provider, "dim_provider")
    load.load_table(conn, fact_encounters, "fact_encounters")
    load.load_table(conn, fact_conditions, "fact_conditions")
    load.load_table(conn, fact_medications, "fact_medications")
    load.load_table(conn, fact_procedures, "fact_procedures")
    load.load_table(conn, fact_observations, "fact_observations")
    conn.commit()

    # --- VALIDATE ---
    passed = run_quality_checks(conn)
    conn.close()

    elapsed = time.time() - start
    if passed:
        log.info(f"=== Pipeline completed successfully in {elapsed:.1f}s. Warehouse at {DB_PATH} ===")
    else:
        log.error(f"=== Pipeline completed with QUALITY CHECK FAILURES in {elapsed:.1f}s ===")
        sys.exit(1)


if __name__ == "__main__":
    main()
