import uuid
import numpy as np
import pandas as pd
from app.db import engine
from scripts.common import find_file, read_csv_flexible


def find_inventory_file():
    preferred_names = [
        "salesdaily",
        "sales_daily",
        "saleshourly",
        "salesweekly",
        "salesmonthly",
        "sales"
    ]

    for name in preferred_names:
        path = find_file(name)
        if path is not None:
            return path

    return None


def detect_date_column(df):
    possible = ["datum", "date", "sale_date", "datetime", "timestamp"]

    for col in df.columns:
        if col.lower() in possible:
            return col

    return df.columns[0]


def convert_sales_to_long(df):
    date_col = detect_date_column(df)

    # Wide format: datum, M01AB, M01AE, N02BA...
    numeric_cols = []

    for col in df.columns:
        if col == date_col:
            continue

        converted = pd.to_numeric(df[col], errors="coerce")

        if converted.notna().sum() > 0:
            numeric_cols.append(col)

    if len(numeric_cols) >= 2:
        long_df = df.melt(
            id_vars=[date_col],
            value_vars=numeric_cols,
            var_name="medication_name",
            value_name="quantity_sold"
        )

        long_df = long_df.rename(columns={date_col: "sale_date"})
        return long_df

    # Transaction format fallback
    date_candidates = [c for c in df.columns if "date" in c.lower() or "datum" in c.lower()]
    med_candidates = [c for c in df.columns if "drug" in c.lower() or "med" in c.lower() or "brand" in c.lower()]
    qty_candidates = [c for c in df.columns if "qty" in c.lower() or "quantity" in c.lower() or "sold" in c.lower()]

    if not date_candidates or not med_candidates or not qty_candidates:
        raise ValueError("Could not detect inventory sales columns.")

    out = df.rename(
        columns={
            date_candidates[0]: "sale_date",
            med_candidates[0]: "medication_name",
            qty_candidates[0]: "quantity_sold"
        }
    )

    return out[["sale_date", "medication_name", "quantity_sold"]]


def load_pharmacy_sales():
    path = find_inventory_file()

    if path is None:
        print("No Kaggle pharma sales file found.")
        return pd.DataFrame()

    df = read_csv_flexible(path)

    sales = convert_sales_to_long(df)

    sales["sale_date"] = pd.to_datetime(sales["sale_date"], errors="coerce")
    sales["quantity_sold"] = pd.to_numeric(sales["quantity_sold"], errors="coerce").fillna(0)
    sales["medication_name"] = sales["medication_name"].astype(str)

    sales = sales.dropna(subset=["sale_date"])
    sales = sales[sales["quantity_sold"] >= 0]

    sales[["sale_date", "medication_name", "quantity_sold"]].to_sql(
        "pharmacy_sales",
        engine,
        if_exists="append",
        index=False
    )

    print(f"Loaded pharmacy sales rows: {len(sales)}")

    return sales


def build_inventory_from_sales(sales):
    if sales.empty:
        print("No sales data available to build inventory.")
        return

    daily = (
        sales
        .groupby(["medication_name", sales["sale_date"].dt.date])["quantity_sold"]
        .sum()
        .reset_index()
    )

    avg_usage = (
        daily
        .groupby("medication_name")["quantity_sold"]
        .mean()
        .reset_index()
        .rename(columns={"quantity_sold": "avg_daily_usage"})
    )

    rows = []

    suppliers = ["McKesson", "Cardinal Health", "AmerisourceBergen", "Hospital Central Supply"]
    dosage_forms = ["tablet", "capsule", "vial", "IV bag", "syringe"]

    rng = np.random.default_rng(42)

    for i, row in avg_usage.iterrows():
        medication_name = str(row["medication_name"])
        avg_daily_usage = float(row["avg_daily_usage"])

        if avg_daily_usage <= 0:
            avg_daily_usage = 0.1

        quantity_on_hand = int(max(rng.normal(avg_daily_usage * 10, avg_daily_usage * 4), 1))
        par_level = int(max(avg_daily_usage * 14, 10))

        predicted_days = round(quantity_on_hand / avg_daily_usage, 2)
        reorder_recommendation = max(par_level - quantity_on_hand, 0)

        if predicted_days <= 3:
            shortage_status = "critical"
        elif predicted_days <= 7:
            shortage_status = "low"
        elif predicted_days <= 14:
            shortage_status = "watch"
        else:
            shortage_status = "stable"

        rows.append({
            "medication_id": f"inv-{uuid.uuid4().hex[:12]}",
            "medication_name": medication_name,
            "dosage_form": dosage_forms[i % len(dosage_forms)],
            "quantity_on_hand": quantity_on_hand,
            "par_level": par_level,
            "avg_daily_usage": round(avg_daily_usage, 2),
            "predicted_days_on_hand": predicted_days,
            "reorder_recommendation": int(reorder_recommendation),
            "unit_cost": round(float(rng.uniform(2, 250)), 2),
            "supplier": suppliers[i % len(suppliers)],
            "shortage_status": shortage_status
        })

    inventory = pd.DataFrame(rows)

    inventory.to_sql(
        "pharmacy_inventory",
        engine,
        if_exists="append",
        index=False
    )

    print(f"Built inventory rows: {len(inventory)}")


def main():
    sales = load_pharmacy_sales()
    build_inventory_from_sales(sales)


if __name__ == "__main__":
    main()