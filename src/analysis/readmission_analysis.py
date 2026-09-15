"""
Analysis on top of the warehouse:
  1. 30-day inpatient readmission rate (a standard hospital quality metric)
  2. Top chronic conditions by prevalence
  3. Average cost per encounter by encounter class

Outputs CSVs + a couple of PNG charts to data/processed/.

Usage:
    python -m src.analysis.readmission_analysis
"""
import logging
import sys
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.etl.config import DB_PATH, PROCESSED_DIR
from src.etl.load import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)


def readmission_rate(conn) -> pd.DataFrame:
    """
    For every inpatient discharge, flag whether the same patient had
    another inpatient encounter starting within 30 days.
    """
    inpatient = pd.read_sql("""
        SELECT encounter_id, patient_id, start_date_key, stop_date_key
        FROM fact_encounters
        WHERE encounter_class = 'inpatient'
        ORDER BY patient_id, start_date_key
    """, conn, parse_dates=["start_date_key", "stop_date_key"])

    if inpatient.empty:
        log.warning("No inpatient encounters found — skipping readmission analysis.")
        return pd.DataFrame()

    inpatient["readmitted_within_30d"] = False
    for patient_id, grp in inpatient.groupby("patient_id"):
        grp = grp.sort_values("start_date_key")
        stops = grp["stop_date_key"].values
        starts = grp["start_date_key"].values
        idx = grp.index.to_list()
        for i in range(len(idx) - 1):
            gap_days = (starts[i + 1] - stops[i]) / pd.Timedelta(days=1)
            if 0 <= gap_days <= 30:
                inpatient.loc[idx[i], "readmitted_within_30d"] = True

    rate = inpatient["readmitted_within_30d"].mean() * 100
    log.info(f"30-day inpatient readmission rate: {rate:.1f}% "
              f"({inpatient['readmitted_within_30d'].sum()} of {len(inpatient)} discharges)")
    return inpatient


def top_chronic_conditions(conn, n: int = 15) -> pd.DataFrame:
    """
    Synthea's `conditions` table mixes true clinical diagnoses -- coded as
    SNOMED "(disorder)" or "(finding)" terms like diabetes or hypertension --
    with social-determinants-of-health (SDOH) codes such as employment
    status or social isolation, which Synthea also models as "conditions".
    Mixing these produces a misleading "top conditions" list (e.g. "Full-time
    employment" outranking real diagnoses), so we split them: SDOH terms are
    reported separately as a population-health view rather than dropped.
    """
    sdoh_descriptions = [
        "Full-time employment (finding)", "Part-time employment (finding)",
        "Not in labor force (finding)", "Unemployed (finding)",
        "Received higher education (finding)", "Educated to high school level (finding)",
        "Only received primary school education (finding)", "Social isolation (finding)",
        "Limited social contact (finding)", "Stress (finding)",
        "Has a criminal record (finding)", "Homeless (finding)",
        "Housing unsatisfactory (finding)", "Lack of access to transportation (finding)",
        "Transport problem (finding)", "Refugee (person)",
        "Serving in military service (finding)", "Reports of violence in the environment (finding)",
        "Risk activity involvement (finding)", "Misuses drugs (finding)",
        "Unhealthy alcohol drinking behavior (finding)", "Victim of intimate partner abuse (finding)",
        "Medication review due (situation)", "Sterilization requested (situation)",
    ]
    placeholders = ", ".join(f"'{d}'" for d in sdoh_descriptions)
    exclude_clause = f"description NOT IN ({placeholders})"

    clinical = pd.read_sql(f"""
        SELECT description, COUNT(DISTINCT patient_id) AS patient_count
        FROM fact_conditions
        WHERE {exclude_clause}
        GROUP BY description
        ORDER BY patient_count DESC
        LIMIT {n}
    """, conn)

    sdoh = pd.read_sql(f"""
        SELECT description, COUNT(DISTINCT patient_id) AS patient_count
        FROM fact_conditions
        WHERE description IN ({placeholders})
        GROUP BY description
        ORDER BY patient_count DESC
    """, conn)

    log.info(f"Top clinical condition: {clinical.iloc[0]['description']} "
              f"({clinical.iloc[0]['patient_count']} patients)")
    sdoh.to_csv(PROCESSED_DIR / "sdoh_prevalence.csv", index=False)
    return clinical


def avg_cost_by_encounter_class(conn) -> pd.DataFrame:
    df = pd.read_sql("""
        SELECT encounter_class,
               COUNT(*) AS n_encounters,
               ROUND(AVG(total_claim_cost), 2) AS avg_claim_cost,
               ROUND(SUM(total_claim_cost), 2) AS total_claim_cost
        FROM fact_encounters
        GROUP BY encounter_class
        ORDER BY avg_claim_cost DESC
    """, conn)
    return df


def main():
    conn = get_connection()

    readmit_df = readmission_rate(conn)
    if not readmit_df.empty:
        readmit_df.to_csv(PROCESSED_DIR / "readmission_flags.csv", index=False)

    chronic_df = top_chronic_conditions(conn)
    chronic_df.to_csv(PROCESSED_DIR / "top_chronic_conditions.csv", index=False)

    cost_df = avg_cost_by_encounter_class(conn)
    cost_df.to_csv(PROCESSED_DIR / "avg_cost_by_encounter_class.csv", index=False)

    # --- Charts ---
    fig, ax = plt.subplots(figsize=(10, 6.5))
    ax.barh(chronic_df["description"][::-1], chronic_df["patient_count"][::-1], color="#2b6cb0")
    ax.set_xlabel("Number of patients")
    ax.set_title("Top 15 Clinical Conditions by Patient Prevalence\n(Synthetic EHR Cohort, n=334)")
    plt.tight_layout()
    fig.savefig(PROCESSED_DIR / "top_conditions.png", dpi=150)
    log.info(f"Saved chart: {PROCESSED_DIR / 'top_conditions.png'}")

    fig2, ax2 = plt.subplots(figsize=(8, 5))
    ax2.bar(cost_df["encounter_class"], cost_df["avg_claim_cost"], color="#c05621")
    ax2.set_ylabel("Avg claim cost ($)")
    ax2.set_title("Average Claim Cost by Encounter Class")
    plt.tight_layout()
    fig2.savefig(PROCESSED_DIR / "avg_cost_by_class.png", dpi=150)
    log.info(f"Saved chart: {PROCESSED_DIR / 'avg_cost_by_class.png'}")

    conn.close()
    log.info("Analysis complete. Outputs in data/processed/")


if __name__ == "__main__":
    main()
