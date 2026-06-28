import uuid
import pandas as pd
from app.db import engine


def seed_medrec_fallback():
    existing = pd.read_sql(
        "SELECT COUNT(*) AS count FROM medication_reconciliation",
        engine
    )

    if int(existing.iloc[0]["count"]) > 0:
        print("Medication reconciliation rows already exist. Skipping.")
        return

    inpatient = pd.read_sql(
        """
        SELECT patient_id, admission_id, medication_name
        FROM medication_orders
        WHERE medication_name IS NOT NULL
        ORDER BY risk_score DESC NULLS LAST
        LIMIT 1000
        """,
        engine
    )

    if inpatient.empty:
        print("No medication orders found. Run scripts/load_mimic.py first.")
        return

    common_home_meds = [
        "Metformin 500 mg tablet",
        "Lisinopril 10 mg tablet",
        "Atorvastatin 40 mg tablet",
        "Amlodipine 5 mg tablet",
        "Levothyroxine 50 mcg tablet",
        "Omeprazole 20 mg capsule",
        "Aspirin 81 mg tablet",
        "Furosemide 20 mg tablet",
        "Gabapentin 300 mg capsule",
        "Sertraline 50 mg tablet",
        "Warfarin 5 mg tablet",
        "Insulin glargine injection"
    ]

    discrepancy_types = [
        "omission",
        "dose mismatch",
        "frequency mismatch",
        "duplication",
        "allergy conflict",
        "matched"
    ]

    severity_map = {
        "omission": "medium",
        "dose mismatch": "medium",
        "frequency mismatch": "low",
        "duplication": "high",
        "allergy conflict": "high",
        "matched": "low"
    }

    notes = {
        "omission": "Home medication not found in inpatient list. Clarify intentional hold with provider.",
        "dose mismatch": "Home medication appears continued with different dose. Verify intended dose.",
        "frequency mismatch": "Home medication appears continued with different frequency. Verify schedule.",
        "duplication": "Possible therapeutic duplication. Review active inpatient medications.",
        "allergy conflict": "Potential medication allergy conflict. Verify allergy history before continuation.",
        "matched": "Home medication appears represented in inpatient medication list."
    }

    rows = []

    sample = inpatient.drop_duplicates(subset=["patient_id", "admission_id"]).head(150)

    for index, row in sample.reset_index(drop=True).iterrows():
        discrepancy_type = discrepancy_types[index % len(discrepancy_types)]
        home_med = common_home_meds[index % len(common_home_meds)]

        inpatient_med = None

        if discrepancy_type in ["matched", "dose mismatch", "frequency mismatch", "duplication"]:
            inpatient_med = row["medication_name"]

        rows.append({
            "reconciliation_id": f"medrec-demo-{uuid.uuid4().hex[:12]}",
            "patient_id": row["patient_id"],
            "admission_id": row["admission_id"],
            "home_medication": home_med,
            "inpatient_medication": inpatient_med,
            "discrepancy_type": discrepancy_type,
            "severity": severity_map[discrepancy_type],
            "status": "resolved" if discrepancy_type == "matched" else "open",
            "pharmacist_note": notes[discrepancy_type]
        })

    out = pd.DataFrame(rows)

    out.to_sql(
        "medication_reconciliation",
        engine,
        if_exists="append",
        index=False
    )

    print(f"Created fallback medication reconciliation rows: {len(out)}")


if __name__ == "__main__":
    seed_medrec_fallback()