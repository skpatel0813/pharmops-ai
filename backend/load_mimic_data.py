import os
import glob
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv


# ---------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL is missing. Make sure backend/.env exists and contains:\n"
        "DATABASE_URL=postgresql://postgres:admin@localhost:5432/pharmops_ai"
    )

print(f"Using database URL: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)


# ---------------------------------------------------------
# Raw data location
# ---------------------------------------------------------

RAW_DIR = PROJECT_DIR / "data" / "raw"


def find_file(name_contains):
    pattern = str(RAW_DIR / "**" / f"*{name_contains}*.csv*")
    matches = glob.glob(pattern, recursive=True)

    if not matches:
        raise FileNotFoundError(
            f"Could not find file containing: {name_contains}\n"
            f"Searched inside: {RAW_DIR}"
        )

    print(f"Found {name_contains} file: {matches[0]}")
    return matches[0]


# ---------------------------------------------------------
# Load patients
# ---------------------------------------------------------

def load_patients():
    path = find_file("patients")
    df = pd.read_csv(path, compression="infer")

    patients = df.rename(columns={
        "subject_id": "patient_id"
    })

    cols = [
        "patient_id",
        "gender",
        "anchor_age",
        "anchor_year"
    ]

    patients = patients[[c for c in cols if c in patients.columns]]
    patients = patients.drop_duplicates(subset=["patient_id"])

    patients.to_sql("patients", engine, if_exists="append", index=False)

    print(f"Loaded patients: {len(patients)}")


# ---------------------------------------------------------
# Load admissions
# ---------------------------------------------------------

def load_admissions():
    path = find_file("admissions")
    df = pd.read_csv(path, compression="infer")

    admissions = df.rename(columns={
        "subject_id": "patient_id",
        "hadm_id": "admission_id",
        "admittime": "admit_time",
        "dischtime": "discharge_time"
    })

    cols = [
        "admission_id",
        "patient_id",
        "admit_time",
        "discharge_time",
        "admission_type",
        "insurance",
        "language",
        "marital_status",
        "race"
    ]

    admissions = admissions[[c for c in cols if c in admissions.columns]]
    admissions = admissions.drop_duplicates(subset=["admission_id"])

    admissions.to_sql("admissions", engine, if_exists="append", index=False)

    print(f"Loaded admissions: {len(admissions)}")


# ---------------------------------------------------------
# Risk scoring
# ---------------------------------------------------------

def calculate_risk(row):
    risk = 20
    reasons = []

    med = str(row.get("drug", "")).lower()
    route = str(row.get("route", "")).lower()

    high_alert_meds = [
        "heparin",
        "warfarin",
        "insulin",
        "vancomycin",
        "morphine",
        "hydromorphone",
        "fentanyl",
        "potassium"
    ]

    antibiotics = [
        "vancomycin",
        "cefepime",
        "ceftriaxone",
        "piperacillin",
        "meropenem",
        "levofloxacin"
    ]

    if any(x in med for x in high_alert_meds):
        risk += 35
        reasons.append("high-alert medication")

    if any(x in med for x in antibiotics):
        risk += 20
        reasons.append("antibiotic stewardship review")

    if "iv" in route or "intravenous" in route:
        risk += 10
        reasons.append("IV medication")

    if pd.isna(row.get("stoptime")):
        risk += 10
        reasons.append("missing stop time")

    risk = min(risk, 100)

    if risk >= 75:
        level = "high"
    elif risk >= 45:
        level = "medium"
    else:
        level = "low"

    return risk, level, ", ".join(reasons)


# ---------------------------------------------------------
# Load medication orders
# ---------------------------------------------------------

def load_medication_orders():
    path = find_file("prescriptions")
    df = pd.read_csv(path, compression="infer")

    # Limit for portfolio/demo project
    df = df.head(5000)

    rows = []

    for index, row in df.iterrows():
        risk, level, reasons = calculate_risk(row)

        pharmacy_id = row.get("pharmacy_id")

        if pd.notna(pharmacy_id) and str(pharmacy_id).strip():
            order_id = str(pharmacy_id)
        else:
            order_id = f"rx-{index}"

        rows.append({
            "order_id": order_id,
            "patient_id": str(row.get("subject_id")),
            "admission_id": str(row.get("hadm_id")),
            "medication_name": row.get("drug"),
            "dose": row.get("dose_val_rx"),
            "route": row.get("route"),
            "frequency": row.get("doses_per_24_hrs"),
            "start_time": row.get("starttime"),
            "stop_time": row.get("stoptime"),
            "priority": "STAT" if risk >= 75 else "Routine",
            "verification_status": "pending",
            "risk_score": risk,
            "risk_level": level,
            "risk_reasons": reasons
        })

    orders = pd.DataFrame(rows)
    orders = orders.drop_duplicates(subset=["order_id"])

    orders.to_sql("medication_orders", engine, if_exists="append", index=False)

    print(f"Loaded medication orders: {len(orders)}")


# ---------------------------------------------------------
# Load antibiotic reviews
# ---------------------------------------------------------

def load_antibiotic_reviews():
    path = find_file("prescriptions")
    df = pd.read_csv(path, compression="infer")

    antibiotics = [
        "vancomycin",
        "cefepime",
        "ceftriaxone",
        "piperacillin",
        "meropenem",
        "levofloxacin",
        "azithromycin",
        "metronidazole",
        "cefazolin"
    ]

    if "drug" not in df.columns:
        raise KeyError("The prescriptions file does not contain a 'drug' column.")

    df["drug_lower"] = df["drug"].astype(str).str.lower()

    abx = df[df["drug_lower"].apply(lambda x: any(a in x for a in antibiotics))]
    abx = abx.head(2000)

    rows = []

    for index, row in abx.iterrows():
        start = pd.to_datetime(row.get("starttime"), errors="coerce")
        stop = pd.to_datetime(row.get("stoptime"), errors="coerce")

        if pd.notna(start) and pd.notna(stop):
            days = max((stop - start).total_seconds() / 86400, 0)
        else:
            days = None

        route = str(row.get("route", "")).lower()

        rows.append({
            "review_id": f"abx-{index}",
            "patient_id": str(row.get("subject_id")),
            "admission_id": str(row.get("hadm_id")),
            "antibiotic_name": row.get("drug"),
            "start_time": row.get("starttime"),
            "stop_time": row.get("stoptime"),
            "days_of_therapy": days,
            "culture_status": "pending",
            "stop_date_present": pd.notna(stop),
            "iv_to_po_candidate": route in ["iv", "intravenous"],
            "deescalation_candidate": days is not None and days >= 3,
            "review_status": "needs_review"
        })

    reviews = pd.DataFrame(rows)

    if reviews.empty:
        print("Loaded antibiotic reviews: 0")
        return

    reviews = reviews.drop_duplicates(subset=["review_id"])

    reviews.to_sql("antibiotic_reviews", engine, if_exists="append", index=False)

    print(f"Loaded antibiotic reviews: {len(reviews)}")


# ---------------------------------------------------------
# Main runner
# ---------------------------------------------------------

if __name__ == "__main__":
    print("Starting MIMIC data load...")
    print(f"Backend folder: {BASE_DIR}")
    print(f"Raw data folder: {RAW_DIR}")

    load_patients()
    load_admissions()
    load_medication_orders()
    load_antibiotic_reviews()

    print("MIMIC data load complete.")