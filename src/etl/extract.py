"""
Extract: read Synthea's raw CSV exports into pandas DataFrames.

Synthea (https://github.com/synthetichealth/synthea) is an open-source
synthetic patient generator. Each run produces a self-consistent set of
CSVs (patients, encounters, conditions, medications, procedures,
observations, providers, organizations) with realistic longitudinal
patient histories -- no real PHI involved.
"""
import logging
import pandas as pd
from .config import RAW_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# Only the columns each downstream table actually needs -- keeps memory
# down on the larger files (observations, claims_transactions, etc.)
USECOLS = {
    "patients.csv": [
        "Id", "BIRTHDATE", "DEATHDATE", "MARITAL", "RACE", "ETHNICITY",
        "GENDER", "CITY", "STATE", "COUNTY", "ZIP",
        "HEALTHCARE_EXPENSES", "HEALTHCARE_COVERAGE",
    ],
    "organizations.csv": ["Id", "NAME", "CITY", "STATE", "ZIP"],
    "providers.csv": ["Id", "ORGANIZATION", "NAME", "GENDER", "SPECIALITY", "CITY", "STATE"],
    "encounters.csv": [
        "Id", "START", "STOP", "PATIENT", "ORGANIZATION", "PROVIDER",
        "ENCOUNTERCLASS", "CODE", "DESCRIPTION", "BASE_ENCOUNTER_COST",
        "TOTAL_CLAIM_COST", "PAYER_COVERAGE", "REASONCODE", "REASONDESCRIPTION",
    ],
    "conditions.csv": ["START", "STOP", "PATIENT", "ENCOUNTER", "CODE", "DESCRIPTION"],
    "medications.csv": [
        "START", "STOP", "PATIENT", "ENCOUNTER", "CODE", "DESCRIPTION",
        "BASE_COST", "PAYER_COVERAGE", "DISPENSES", "TOTALCOST",
        "REASONCODE", "REASONDESCRIPTION",
    ],
    "procedures.csv": [
        "START", "STOP", "PATIENT", "ENCOUNTER", "CODE", "DESCRIPTION",
        "BASE_COST", "REASONCODE", "REASONDESCRIPTION",
    ],
    "observations.csv": ["DATE", "PATIENT", "ENCOUNTER", "CODE", "DESCRIPTION", "VALUE", "UNITS", "TYPE"],
}


def read_csv(name: str) -> pd.DataFrame:
    path = RAW_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run `bash src/generate_data.sh` first to "
            f"generate the Synthea CSV export."
        )
    df = pd.read_csv(path, usecols=USECOLS.get(name), low_memory=False)
    log.info(f"Extracted {len(df):,} rows from {name}")
    return df


def extract_all() -> dict:
    """Read every raw source table needed for the warehouse."""
    return {
        "patients": read_csv("patients.csv"),
        "organizations": read_csv("organizations.csv"),
        "providers": read_csv("providers.csv"),
        "encounters": read_csv("encounters.csv"),
        "conditions": read_csv("conditions.csv"),
        "medications": read_csv("medications.csv"),
        "procedures": read_csv("procedures.csv"),
        "observations": read_csv("observations.csv"),
    }
