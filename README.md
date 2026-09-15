# Synthetic EHR Patient Journey Pipeline

An end-to-end data engineering pipeline that generates a realistic synthetic
patient population, models it into a star-schema data warehouse, runs
automated data quality checks, and produces health-analytics outputs
(30-day readmission rate, chronic condition prevalence, cost-by-encounter-type).

Built to demonstrate the full pipeline lifecycle — **generation → ETL →
schema design → data quality → analysis** — on realistic-scale healthcare
data (10 years of longitudinal history per patient, ~300K total clinical
events) without touching any real patient data.

## Why synthetic data

[Synthea](https://github.com/synthetichealth/synthea) is an open-source
synthetic patient generator built by MITRE specifically so students and
engineers can work with FHIR/HL7-consistent, longitudinally realistic EHR
data with zero PHI risk. Every patient, encounter, diagnosis, and
prescription in this project is fabricated but statistically and clinically
plausible — modeled on real disease progression, care pathways, and cost
patterns.

## Architecture

```
Synthea (Java)  →  raw CSVs  →  Python ETL  →  SQLite star schema  →  analysis
  generates         (18 files,    extract /      (warehouse with       (readmission
  synthetic         ~300K rows)   transform /     quality-checked        rate, chronic
  patients                        load             fact/dim tables)      conditions,
                                                                          cost analysis)
```

**Star schema** (`sql/schema.sql`):
- **Dimensions:** `dim_patient`, `dim_provider`, `dim_organization`, `dim_date`
- **Facts:** `fact_encounters`, `fact_conditions`, `fact_medications`, `fact_procedures`, `fact_observations`

This mirrors how a real healthcare data team would model claims/EHR data for
BI tools (Tableau/Power BI connect cleanly to a star schema), and is
portable to Postgres/Snowflake/BigQuery with minimal changes — SQLite was
chosen here for zero-setup reproducibility.

## What's in the sample run

A generated run of 334 synthetic patients (Virginia, 10 years of history)
produced:

| Table | Rows |
|---|---|
| Encounters | ~18,000 |
| Conditions | ~11,000 |
| Medications | ~14,500 |
| Procedures | ~49,000 |
| Observations (vitals/labs) | ~216,000 |

Pipeline runtime: **~4 seconds** end-to-end (extract → transform → load → validate) on this volume.

## Data quality checks

`src/etl/run_pipeline.py` runs an automated validation gate after every
load — the pipeline fails loudly (non-zero exit code) rather than silently
loading bad data:
- Primary key uniqueness on every dimension table
- Referential integrity: no fact row may reference a `patient_id` that
  doesn't exist in `dim_patient`
- NOT NULL checks on critical columns (`patient_id`, `birthdate`, `encounter_class`, etc.)

## Analysis outputs

`src/analysis/readmission_analysis.py` produces:
1. **30-day inpatient readmission rate** — a standard hospital quality
   metric, computed by flagging any inpatient discharge followed by another
   inpatient admission for the same patient within 30 days. (17.1% in the
   sample run — 61 of 356 discharges.)
2. **Top clinical conditions by prevalence** — with a deliberate split from
   social-determinants-of-health (SDOH) codes. Synthea's `conditions` table
   mixes true clinical diagnoses with SDOH findings (employment status,
   housing, social isolation); naively grouping them produces a misleading
   "top conditions" list where "Full-time employment" outranks real
   diagnoses. This pipeline separates them into `top_chronic_conditions.csv`
   and `sdoh_prevalence.csv` — a data-cleaning judgment call worth noting
   since it reflects the kind of messiness real EHR data actually has.
3. **Average claim cost by encounter class** (ambulatory / emergency /
   inpatient / wellness / urgent care).

## Getting started

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Generate synthetic patient data (requires Java 11+)
bash src/generate_data.sh 300 Virginia   # population size, state

# 3. Run the ETL pipeline (extract -> transform -> load -> validate)
python -m src.etl.run_pipeline

# 4. Run the analysis layer
python -m src.analysis.readmission_analysis

# 5. Run tests
pytest tests/ -v
```

Outputs land in `data/processed/`: `ehr_warehouse.db` (the SQLite
warehouse), CSV exports of each analysis, and two PNG charts.

## Project structure

```
synthetic-ehr-pipeline/
├── src/
│   ├── generate_data.sh       # wraps Synthea to produce raw CSVs
│   ├── etl/
│   │   ├── extract.py         # read raw CSVs
│   │   ├── transform.py       # clean + reshape into star schema
│   │   ├── load.py            # create schema, bulk load SQLite
│   │   ├── run_pipeline.py    # orchestrator + data quality gate
│   │   └── config.py
│   └── analysis/
│       └── readmission_analysis.py
├── sql/
│   └── schema.sql             # star schema DDL
├── tests/
│   └── test_transform.py      # unit tests on transform logic
├── data/
│   ├── raw/                   # Synthea CSVs (gitignored, regenerable)
│   └── processed/             # warehouse + analysis outputs (gitignored)
├── requirements.txt
└── README.md
```

## Tech stack

Python (pandas), SQLite, SQL (DDL + analytical queries), Synthea (Java),
matplotlib, pytest.

## Possible extensions

- Swap SQLite for Postgres/Snowflake and orchestrate with Airflow/Prefect for scheduled runs
- Add dbt on top of the raw load for declarative transformation + built-in testing
- Build a Tableau/Power BI dashboard directly on the warehouse tables
- Extend the readmission analysis into a predictive model (see companion idea: hospital readmission risk classifier)

## Disclaimer

All data in this project is synthetic, generated by Synthea. No real
patient data was used at any point.
