"""
Unit tests for the transform layer. Uses small hand-built DataFrames
rather than the full Synthea export, so tests run in well under a second
and don't depend on data having been generated.

Run with: pytest tests/
"""
import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from src.etl import transform


def test_build_dim_patient_deduplicates():
    raw = pd.DataFrame({
        "Id": ["p1", "p1", "p2"],
        "BIRTHDATE": ["2000-01-01", "2000-01-01", "1990-05-05"],
        "DEATHDATE": [None, None, None],
        "MARITAL": ["M", "M", "S"],
        "RACE": ["white", "white", "black"],
        "ETHNICITY": ["nonhispanic", "nonhispanic", "hispanic"],
        "GENDER": ["F", "F", "M"],
        "CITY": ["Fairfax", "Fairfax", "Arlington"],
        "STATE": ["VA", "VA", "VA"],
        "COUNTY": ["Fairfax", "Fairfax", "Arlington"],
        "ZIP": ["22030", "22030", "22201"],
        "HEALTHCARE_EXPENSES": [100.0, 100.0, 200.0],
        "HEALTHCARE_COVERAGE": [50.0, 50.0, 75.0],
    })
    dim = transform.build_dim_patient(raw)
    assert len(dim) == 2, "duplicate patient_id rows should be collapsed"
    assert dim["patient_id"].is_unique


def test_build_dim_patient_deceased_flag():
    raw = pd.DataFrame({
        "Id": ["p1", "p2"],
        "BIRTHDATE": ["2000-01-01", "1990-05-05"],
        "DEATHDATE": ["2020-01-01", None],
        "MARITAL": ["M", "S"], "RACE": ["white", "black"],
        "ETHNICITY": ["nonhispanic", "hispanic"], "GENDER": ["F", "M"],
        "CITY": ["Fairfax", "Arlington"], "STATE": ["VA", "VA"],
        "COUNTY": ["Fairfax", "Arlington"], "ZIP": ["22030", "22201"],
        "HEALTHCARE_EXPENSES": [100.0, 200.0], "HEALTHCARE_COVERAGE": [50.0, 75.0],
    })
    dim = transform.build_dim_patient(raw)
    assert dim.set_index("patient_id").loc["p1", "is_deceased"] == 1
    assert dim.set_index("patient_id").loc["p2", "is_deceased"] == 0


def test_fact_encounters_date_keys_are_date_only():
    raw = pd.DataFrame({
        "Id": ["e1"], "PATIENT": ["p1"], "PROVIDER": ["pr1"], "ORGANIZATION": ["o1"],
        "START": ["2020-03-15T12:00:00Z"], "STOP": ["2020-03-15T13:30:00Z"],
        "ENCOUNTERCLASS": ["ambulatory"], "CODE": ["123"], "DESCRIPTION": ["Checkup"],
        "BASE_ENCOUNTER_COST": [100.0], "TOTAL_CLAIM_COST": [150.0], "PAYER_COVERAGE": [120.0],
        "REASONCODE": [None], "REASONDESCRIPTION": [None],
    })
    fact = transform.build_fact_encounters(raw)
    assert fact.loc[0, "start_date_key"] == "2020-03-15"
    assert fact.loc[0, "stop_date_key"] == "2020-03-15"


def test_dim_date_covers_all_input_dates():
    s1 = pd.Series(["2020-01-01", "2020-01-05"])
    s2 = pd.Series(["2020-01-03", None])
    dim = transform.build_dim_date(s1, s2)
    assert set(dim["date_key"]) == {"2020-01-01", "2020-01-03", "2020-01-05"}
    assert dim.loc[dim["date_key"] == "2020-01-01", "day_of_week"].iloc[0] == 2  # Wednesday
