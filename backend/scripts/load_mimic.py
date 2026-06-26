import uuid
import pandas as pd
from sqlalchemy import text
from app.db import engine
from scripts.common import (
    find_file,
    read_csv_flexible,
    clean_id,
    normalize_text,
    med_tokens
)


HIGH_ALERT_MEDS = [
    "heparin",
    "warfarin",
    "insulin",
    "vancomycin",
    "morphine",
    "hydromorphone",
    "fentanyl",
    "potassium",
    "norepinephrine",
    "epinephrine",
    "propofol",
    "tacrolimus"
]

ANTIBIOTICS = [
    "vancomycin",
    "cefepime",
    "ceftriaxone",
    "cefazolin",
    "piperacillin",
    "tazobactam",
    "meropenem",
    "ertapenem",
    "levofloxacin",
    "ciprofloxacin",
    "azithromycin",
    "metronidazole",
    "ampicillin",
    "amoxicillin",
    "gentamicin",
    "tobramycin",
    "clindamycin"
]

BROAD_SPECTRUM = [
    "vancomycin",
    "cefepime",
    "piperacillin",
    "tazobactam",
    "meropenem",
    "ertapenem"
]


def load_patients():
    path = find_file("patients")

    if path is None:
        print("No patients file found.")
        return

    df = read_csv_flexible(path)

    rows = []

    for _, row in df.iterrows():
        rows.append({
            "patient_id": clean_id(row.get("subject_id")),
            "gender": row.get("gender"),
            "anchor_age": row.get("anchor_age"),
            "anchor_year": row.get("anchor_year")
        })

    out = pd.DataFrame(rows).dropna(subset=["patient_id"])
    out = out.drop_duplicates(subset=["patient_id"])

    out.to_sql("patients", engine, if_exists="append", index=False)
    print(f"Loaded patients: {len(out)}")


def load_admissions():
    path = find_file("admissions")

    if path is None:
        print("No admissions file found.")
        return

    df = read_csv_flexible(path)

    rows = []

    for _, row in df.iterrows():
        admission_id = clean_id(row.get("hadm_id"))

        if not admission_id:
            continue

        rows.append({
            "admission_id": admission_id,
            "patient_id": clean_id(row.get("subject_id")),
            "admit_time": row.get("admittime"),
            "discharge_time": row.get("dischtime"),
            "admission_type": row.get("admission_type"),
            "insurance": row.get("insurance"),
            "language": row.get("language"),
            "marital_status": row.get("marital_status"),
            "race": row.get("race")
        })

    out = pd.DataFrame(rows)
    out = out.drop_duplicates(subset=["admission_id"])

    out.to_sql("admissions", engine, if_exists="append", index=False)
    print(f"Loaded admissions: {len(out)}")


def calculate_order_risk(row, age_lookup):
    risk = 15
    reasons = []

    medication = normalize_text(row.get("drug"))
    route = normalize_text(row.get("route"))
    patient_id = clean_id(row.get("subject_id"))
    age = age_lookup.get(patient_id)

    if any(med in medication for med in HIGH_ALERT_MEDS):
        risk += 35
        reasons.append("high-alert medication")

    if any(abx in medication for abx in ANTIBIOTICS):
        risk += 20
        reasons.append("antibiotic stewardship review")

    if "iv" in route or "intravenous" in route:
        risk += 10
        reasons.append("IV medication")

    if pd.isna(row.get("stoptime")) or str(row.get("stoptime")).strip() == "":
        risk += 10
        reasons.append("missing stop time")

    if age is not None and pd.notna(age):
        try:
            if int(age) >= 75:
                risk += 10
                reasons.append("older adult patient")
        except Exception:
            pass

    dose_value = row.get("dose_val_rx")

    try:
        dose_float = float(dose_value)
        if dose_float > 1000:
            risk += 5
            reasons.append("large numeric dose")
    except Exception:
        pass

    risk = min(risk, 100)

    if risk >= 75:
        level = "high"
    elif risk >= 45:
        level = "medium"
    else:
        level = "low"

    if risk >= 75:
        priority = "STAT"
    elif risk >= 45:
        priority = "Urgent"
    else:
        priority = "Routine"

    return risk, level, priority, ", ".join(reasons) if reasons else "standard review"


def get_age_lookup():
    query = "SELECT patient_id, anchor_age FROM patients"

    with engine.connect() as conn:
        rows = conn.execute(text(query)).fetchall()

    return {str(row.patient_id): row.anchor_age for row in rows}


def load_medication_orders():
    path = find_file("prescriptions")

    if path is None:
        print("No prescriptions file found.")
        return

    df = read_csv_flexible(path)

    if df.empty:
        print("Prescriptions file was empty.")
        return

    age_lookup = get_age_lookup()

    rows = []

    for i, row in df.iterrows():
        patient_id = clean_id(row.get("subject_id"))
        admission_id = clean_id(row.get("hadm_id"))

        if not patient_id:
            continue

        pharmacy_id = clean_id(row.get("pharmacy_id"))
        order_id = pharmacy_id if pharmacy_id else f"rx-{patient_id}-{admission_id}-{i}"

        risk, level, priority, reasons = calculate_order_risk(row, age_lookup)

        dose_value = row.get("dose_val_rx")
        dose_unit = row.get("dose_unit_rx")

        rows.append({
            "order_id": order_id,
            "patient_id": patient_id,
            "admission_id": admission_id,
            "medication_name": row.get("drug"),
            "dose": None if pd.isna(dose_value) else str(dose_value),
            "dose_unit": None if pd.isna(dose_unit) else str(dose_unit),
            "route": row.get("route"),
            "frequency": None if pd.isna(row.get("doses_per_24_hrs")) else str(row.get("doses_per_24_hrs")),
            "start_time": row.get("starttime"),
            "stop_time": row.get("stoptime"),
            "priority": priority,
            "verification_status": "pending",
            "pharmacist_note": None,
            "risk_score": risk,
            "risk_level": level,
            "risk_reasons": reasons
        })

    out = pd.DataFrame(rows)
    out = out.dropna(subset=["order_id"])
    out = out.drop_duplicates(subset=["order_id"])

    out.to_sql("medication_orders", engine, if_exists="append", index=False)
    print(f"Loaded medication orders: {len(out)}")


def load_antibiotic_reviews():
    path = find_file("prescriptions")

    if path is None:
        print("No prescriptions file found.")
        return

    df = read_csv_flexible(path)

    micro_path = find_file("microbiologyevents")
    patients_with_micro = set()

    if micro_path is not None:
        micro = read_csv_flexible(micro_path)

        if "subject_id" in micro.columns:
            patients_with_micro = set(micro["subject_id"].dropna().astype(str).tolist())

    rows = []

    for i, row in df.iterrows():
        medication = normalize_text(row.get("drug"))

        if not any(abx in medication for abx in ANTIBIOTICS):
            continue

        patient_id = clean_id(row.get("subject_id"))
        admission_id = clean_id(row.get("hadm_id"))

        start = pd.to_datetime(row.get("starttime"), errors="coerce")
        stop = pd.to_datetime(row.get("stoptime"), errors="coerce")

        days = None

        if pd.notna(start) and pd.notna(stop):
            days = max(round((stop - start).total_seconds() / 86400, 2), 0)

        stop_date_present = pd.notna(stop)

        route = normalize_text(row.get("route"))
        iv_to_po = "iv" in route or "intravenous" in route

        broad_spectrum = any(abx in medication for abx in BROAD_SPECTRUM)

        deescalation_candidate = bool(
            broad_spectrum and (
                days is not None and days >= 3
            )
        )

        if str(row.get("subject_id")) in patients_with_micro:
            culture_status = "microbiology data present"
        elif micro_path is not None:
            culture_status = "no microbiology record found"
        else:
            culture_status = "microbiology table not loaded"

        rows.append({
            "review_id": f"abx-{uuid.uuid4().hex[:12]}",
            "patient_id": patient_id,
            "admission_id": admission_id,
            "antibiotic_name": row.get("drug"),
            "start_time": row.get("starttime"),
            "stop_time": row.get("stoptime"),
            "days_of_therapy": days,
            "culture_status": culture_status,
            "stop_date_present": bool(stop_date_present),
            "iv_to_po_candidate": bool(iv_to_po),
            "deescalation_candidate": bool(deescalation_candidate),
            "review_status": "needs_review",
            "pharmacist_note": None
        })

    out = pd.DataFrame(rows)

    if out.empty:
        print("No antibiotic rows found.")
        return

    out.to_sql("antibiotic_reviews", engine, if_exists="append", index=False)
    print(f"Loaded antibiotic reviews: {len(out)}")


def load_medication_reconciliation():
    medrecon_path = find_file("medrecon")

    if medrecon_path is None:
        print(
            "No medrecon file found. "
            "Download MIMIC-IV-ED if you want real medication reconciliation rows."
        )
        return

    medrecon = read_csv_flexible(medrecon_path)

    inpatient = pd.read_sql(
        """
        SELECT patient_id, admission_id, medication_name
        FROM medication_orders
        WHERE medication_name IS NOT NULL
        """,
        engine
    )

    patient_to_inpatient_meds = {}

    for _, row in inpatient.iterrows():
        patient_id = str(row["patient_id"])
        patient_to_inpatient_meds.setdefault(patient_id, []).append(row["medication_name"])

    rows = []

    for i, row in medrecon.iterrows():
        patient_id = clean_id(row.get("subject_id"))

        if not patient_id:
            continue

        home_med = row.get("name")

        if pd.isna(home_med) or str(home_med).strip() == "":
            continue

        inpatient_meds = patient_to_inpatient_meds.get(patient_id, [])

        home_tokens = med_tokens(home_med)
        matched_med = None

        for med in inpatient_meds:
            overlap = home_tokens.intersection(med_tokens(med))

            if overlap:
                matched_med = med
                break

        if matched_med:
            discrepancy_type = "matched"
            severity = "low"
            status = "resolved"
            note = "Home medication appears represented in inpatient medication list."
        else:
            discrepancy_type = "omission"
            severity = "medium"
            status = "open"
            note = "Home medication not found in inpatient medication list. Clarify intentional hold."

        stay_id = clean_id(row.get("stay_id"), prefix="edstay")

        rows.append({
            "reconciliation_id": f"medrec-{uuid.uuid4().hex[:12]}",
            "patient_id": patient_id,
            "admission_id": stay_id,
            "home_medication": home_med,
            "inpatient_medication": matched_med,
            "discrepancy_type": discrepancy_type,
            "severity": severity,
            "status": status,
            "pharmacist_note": note
        })

    out = pd.DataFrame(rows)

    if out.empty:
        print("Medrecon file found, but no usable rows were created.")
        return

    out.to_sql("medication_reconciliation", engine, if_exists="append", index=False)
    print(f"Loaded medication reconciliation rows: {len(out)}")


def seed_safety_events():
    orders = pd.read_sql(
        """
        SELECT patient_id, admission_id, medication_name, risk_level, risk_reasons
        FROM medication_orders
        WHERE risk_level IN ('high', 'medium')
        ORDER BY risk_score DESC
        LIMIT 75
        """,
        engine
    )

    if orders.empty:
        print("No medication orders found for safety events.")
        return

    event_types = [
        "duplicate therapy risk",
        "dose clarification",
        "missing stop date",
        "high-alert medication review",
        "renal dosing review"
    ]

    units = ["ICU", "Emergency", "Med-Surg", "Cardiology", "Oncology"]
    causes = ["manual entry", "missing lab", "similar medication", "missing weight", "transition of care"]

    rows = []

    for i, row in orders.iterrows():
        severity = "high" if row["risk_level"] == "high" else "medium"

        rows.append({
            "event_id": f"safe-{uuid.uuid4().hex[:12]}",
            "patient_id": row["patient_id"],
            "admission_id": row["admission_id"],
            "medication_name": row["medication_name"],
            "event_type": event_types[i % len(event_types)],
            "severity": severity,
            "unit": units[i % len(units)],
            "root_cause": causes[i % len(causes)],
            "event_status": "open"
        })

    out = pd.DataFrame(rows)
    out.to_sql("safety_events", engine, if_exists="append", index=False)
    print(f"Seeded safety events: {len(out)}")


def main():
    load_patients()
    load_admissions()
    load_medication_orders()
    load_antibiotic_reviews()
    load_medication_reconciliation()
    seed_safety_events()


if __name__ == "__main__":
    main()