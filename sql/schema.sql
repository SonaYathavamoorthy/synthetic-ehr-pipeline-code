-- ============================================================
-- Synthetic EHR Warehouse — Star Schema
-- Grain: one row per fact event (encounter, condition, medication,
-- procedure, observation), joined to shared dimensions.
-- ============================================================

PRAGMA foreign_keys = ON;

-- ---------------------------
-- DIMENSION TABLES
-- ---------------------------

DROP TABLE IF EXISTS dim_patient;
CREATE TABLE dim_patient (
    patient_id      TEXT PRIMARY KEY,
    birthdate       DATE,
    deathdate       DATE,
    is_deceased     INTEGER,               -- 0/1 flag, derived
    gender          TEXT,
    race            TEXT,
    ethnicity       TEXT,
    marital_status  TEXT,
    city            TEXT,
    state           TEXT,
    county          TEXT,
    zip             TEXT,
    healthcare_expenses  REAL,
    healthcare_coverage  REAL
);

DROP TABLE IF EXISTS dim_organization;
CREATE TABLE dim_organization (
    organization_id TEXT PRIMARY KEY,
    name            TEXT,
    city            TEXT,
    state           TEXT,
    zip             TEXT
);

DROP TABLE IF EXISTS dim_provider;
CREATE TABLE dim_provider (
    provider_id     TEXT PRIMARY KEY,
    organization_id TEXT,
    name            TEXT,
    gender          TEXT,
    specialty       TEXT,
    city            TEXT,
    state           TEXT,
    FOREIGN KEY (organization_id) REFERENCES dim_organization(organization_id)
);

DROP TABLE IF EXISTS dim_date;
CREATE TABLE dim_date (
    date_key    TEXT PRIMARY KEY,   -- 'YYYY-MM-DD'
    year        INTEGER,
    quarter     INTEGER,
    month       INTEGER,
    day         INTEGER,
    day_of_week INTEGER,            -- 0=Monday
    is_weekend  INTEGER
);

-- ---------------------------
-- FACT TABLES
-- ---------------------------

DROP TABLE IF EXISTS fact_encounters;
CREATE TABLE fact_encounters (
    encounter_id     TEXT PRIMARY KEY,
    patient_id       TEXT,
    provider_id      TEXT,
    organization_id  TEXT,
    start_date_key   TEXT,
    stop_date_key    TEXT,
    start_ts         TEXT,
    stop_ts          TEXT,
    encounter_class  TEXT,          -- ambulatory / emergency / inpatient / wellness / urgentcare
    code             TEXT,
    description      TEXT,
    base_encounter_cost REAL,
    total_claim_cost REAL,
    payer_coverage   REAL,
    reason_code      TEXT,
    reason_description TEXT,
    FOREIGN KEY (patient_id) REFERENCES dim_patient(patient_id),
    FOREIGN KEY (provider_id) REFERENCES dim_provider(provider_id),
    FOREIGN KEY (organization_id) REFERENCES dim_organization(organization_id),
    FOREIGN KEY (start_date_key) REFERENCES dim_date(date_key)
);

DROP TABLE IF EXISTS fact_conditions;
CREATE TABLE fact_conditions (
    condition_sk     INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id       TEXT,
    encounter_id     TEXT,
    start_date_key   TEXT,
    stop_date_key    TEXT,
    code             TEXT,
    description      TEXT,
    FOREIGN KEY (patient_id) REFERENCES dim_patient(patient_id),
    FOREIGN KEY (encounter_id) REFERENCES fact_encounters(encounter_id)
);

DROP TABLE IF EXISTS fact_medications;
CREATE TABLE fact_medications (
    medication_sk    INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id       TEXT,
    encounter_id     TEXT,
    start_date_key   TEXT,
    stop_date_key    TEXT,
    code             TEXT,
    description      TEXT,
    base_cost        REAL,
    payer_coverage   REAL,
    dispenses        INTEGER,
    total_cost       REAL,
    reason_code      TEXT,
    reason_description TEXT,
    FOREIGN KEY (patient_id) REFERENCES dim_patient(patient_id),
    FOREIGN KEY (encounter_id) REFERENCES fact_encounters(encounter_id)
);

DROP TABLE IF EXISTS fact_procedures;
CREATE TABLE fact_procedures (
    procedure_sk     INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id       TEXT,
    encounter_id     TEXT,
    date_key         TEXT,
    code             TEXT,
    description      TEXT,
    base_cost        REAL,
    reason_code      TEXT,
    reason_description TEXT,
    FOREIGN KEY (patient_id) REFERENCES dim_patient(patient_id),
    FOREIGN KEY (encounter_id) REFERENCES fact_encounters(encounter_id)
);

DROP TABLE IF EXISTS fact_observations;
CREATE TABLE fact_observations (
    observation_sk   INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id       TEXT,
    encounter_id     TEXT,
    date_key         TEXT,
    code             TEXT,
    description      TEXT,
    value            TEXT,
    units            TEXT,
    obs_type         TEXT,
    FOREIGN KEY (patient_id) REFERENCES dim_patient(patient_id),
    FOREIGN KEY (encounter_id) REFERENCES fact_encounters(encounter_id)
);

-- ---------------------------
-- INDEXES (for analysis-query performance)
-- ---------------------------
CREATE INDEX idx_encounters_patient ON fact_encounters(patient_id);
CREATE INDEX idx_encounters_start   ON fact_encounters(start_date_key);
CREATE INDEX idx_conditions_patient ON fact_conditions(patient_id);
CREATE INDEX idx_conditions_code    ON fact_conditions(code);
CREATE INDEX idx_medications_patient ON fact_medications(patient_id);
CREATE INDEX idx_procedures_patient ON fact_procedures(patient_id);
CREATE INDEX idx_observations_patient ON fact_observations(patient_id);
CREATE INDEX idx_observations_code  ON fact_observations(code);
