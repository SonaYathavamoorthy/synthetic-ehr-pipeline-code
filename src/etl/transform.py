"""
Transform: clean raw Synthea extracts and reshape them into the
dimension/fact tables defined in sql/schema.sql.
"""
import logging
import pandas as pd

log = logging.getLogger(__name__)


def _to_date_key(series: pd.Series) -> pd.Series:
    """Normalize a date/timestamp column to 'YYYY-MM-DD' string keys."""
    return pd.to_datetime(series, errors="coerce", utc=True).dt.strftime("%Y-%m-%d")


def build_dim_patient(patients: pd.DataFrame) -> pd.DataFrame:
    df = patients.copy()
    df["is_deceased"] = df["DEATHDATE"].notna().astype(int)
    df = df.rename(columns={
        "Id": "patient_id", "BIRTHDATE": "birthdate", "DEATHDATE": "deathdate",
        "MARITAL": "marital_status", "RACE": "race", "ETHNICITY": "ethnicity",
        "GENDER": "gender", "CITY": "city", "STATE": "state", "COUNTY": "county",
        "ZIP": "zip", "HEALTHCARE_EXPENSES": "healthcare_expenses",
        "HEALTHCARE_COVERAGE": "healthcare_coverage",
    })
    before = len(df)
    df = df.drop_duplicates(subset="patient_id")
    if len(df) < before:
        log.warning(f"dim_patient: dropped {before - len(df)} duplicate patient_id rows")
    return df[[
        "patient_id", "birthdate", "deathdate", "is_deceased", "gender", "race",
        "ethnicity", "marital_status", "city", "state", "county", "zip",
        "healthcare_expenses", "healthcare_coverage",
    ]]


def build_dim_organization(orgs: pd.DataFrame) -> pd.DataFrame:
    df = orgs.rename(columns={"Id": "organization_id", "NAME": "name", "CITY": "city",
                               "STATE": "state", "ZIP": "zip"})
    return df[["organization_id", "name", "city", "state", "zip"]].drop_duplicates("organization_id")


def build_dim_provider(providers: pd.DataFrame) -> pd.DataFrame:
    df = providers.rename(columns={
        "Id": "provider_id", "ORGANIZATION": "organization_id", "NAME": "name",
        "GENDER": "gender", "SPECIALITY": "specialty", "CITY": "city", "STATE": "state",
    })
    return df[["provider_id", "organization_id", "name", "gender", "specialty",
               "city", "state"]].drop_duplicates("provider_id")


def build_dim_date(*date_series: pd.Series) -> pd.DataFrame:
    """Build a date dimension spanning every date referenced in the fact tables."""
    all_dates = pd.concat(date_series, ignore_index=True).dropna().unique()
    dim = pd.DataFrame({"date_key": all_dates})
    dt = pd.to_datetime(dim["date_key"])
    dim["year"] = dt.dt.year
    dim["quarter"] = dt.dt.quarter
    dim["month"] = dt.dt.month
    dim["day"] = dt.dt.day
    dim["day_of_week"] = dt.dt.dayofweek
    dim["is_weekend"] = (dt.dt.dayofweek >= 5).astype(int)
    return dim.sort_values("date_key").reset_index(drop=True)


def build_fact_encounters(encounters: pd.DataFrame) -> pd.DataFrame:
    df = encounters.copy()
    df["start_date_key"] = _to_date_key(df["START"])
    df["stop_date_key"] = _to_date_key(df["STOP"])
    df = df.rename(columns={
        "Id": "encounter_id", "PATIENT": "patient_id", "PROVIDER": "provider_id",
        "ORGANIZATION": "organization_id", "START": "start_ts", "STOP": "stop_ts",
        "ENCOUNTERCLASS": "encounter_class", "CODE": "code", "DESCRIPTION": "description",
        "BASE_ENCOUNTER_COST": "base_encounter_cost", "TOTAL_CLAIM_COST": "total_claim_cost",
        "PAYER_COVERAGE": "payer_coverage", "REASONCODE": "reason_code",
        "REASONDESCRIPTION": "reason_description",
    })
    return df[[
        "encounter_id", "patient_id", "provider_id", "organization_id",
        "start_date_key", "stop_date_key", "start_ts", "stop_ts", "encounter_class",
        "code", "description", "base_encounter_cost", "total_claim_cost",
        "payer_coverage", "reason_code", "reason_description",
    ]]


def build_fact_conditions(conditions: pd.DataFrame) -> pd.DataFrame:
    df = conditions.copy()
    df["start_date_key"] = _to_date_key(df["START"])
    df["stop_date_key"] = _to_date_key(df["STOP"])
    df = df.rename(columns={"PATIENT": "patient_id", "ENCOUNTER": "encounter_id",
                             "CODE": "code", "DESCRIPTION": "description"})
    return df[["patient_id", "encounter_id", "start_date_key", "stop_date_key", "code", "description"]]


def build_fact_medications(meds: pd.DataFrame) -> pd.DataFrame:
    df = meds.copy()
    df["start_date_key"] = _to_date_key(df["START"])
    df["stop_date_key"] = _to_date_key(df["STOP"])
    df = df.rename(columns={
        "PATIENT": "patient_id", "ENCOUNTER": "encounter_id", "CODE": "code",
        "DESCRIPTION": "description", "BASE_COST": "base_cost",
        "PAYER_COVERAGE": "payer_coverage", "DISPENSES": "dispenses",
        "TOTALCOST": "total_cost", "REASONCODE": "reason_code",
        "REASONDESCRIPTION": "reason_description",
    })
    return df[[
        "patient_id", "encounter_id", "start_date_key", "stop_date_key", "code",
        "description", "base_cost", "payer_coverage", "dispenses", "total_cost",
        "reason_code", "reason_description",
    ]]


def build_fact_procedures(procedures: pd.DataFrame) -> pd.DataFrame:
    df = procedures.copy()
    df["date_key"] = _to_date_key(df["START"])
    df = df.rename(columns={
        "PATIENT": "patient_id", "ENCOUNTER": "encounter_id", "CODE": "code",
        "DESCRIPTION": "description", "BASE_COST": "base_cost",
        "REASONCODE": "reason_code", "REASONDESCRIPTION": "reason_description",
    })
    return df[["patient_id", "encounter_id", "date_key", "code", "description",
               "base_cost", "reason_code", "reason_description"]]


def build_fact_observations(observations: pd.DataFrame) -> pd.DataFrame:
    df = observations.copy()
    df["date_key"] = _to_date_key(df["DATE"])
    df = df.rename(columns={
        "PATIENT": "patient_id", "ENCOUNTER": "encounter_id", "CODE": "code",
        "DESCRIPTION": "description", "VALUE": "value", "UNITS": "units", "TYPE": "obs_type",
    })
    return df[["patient_id", "encounter_id", "date_key", "code", "description",
               "value", "units", "obs_type"]]
