from pathlib import Path
import joblib
import pandas as pd
from sqlalchemy import create_engine
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config import DATABASE_URL


MODEL_PATH = Path(__file__).resolve().parent / "risk_model.joblib"


def contains_any(value, terms):
    value = str(value).lower()
    return int(any(term in value for term in terms))


def main():
    engine = create_engine(DATABASE_URL)

    df = pd.read_sql(
        """
        SELECT
            medication_name,
            route,
            priority,
            risk_score,
            risk_level,
            risk_reasons
        FROM medication_orders
        WHERE risk_level IS NOT NULL
        """,
        engine
    )

    if df.empty:
        raise RuntimeError("No medication orders found. Run scripts/load_mimic.py first.")

    high_alert = [
        "heparin",
        "warfarin",
        "insulin",
        "vancomycin",
        "morphine",
        "fentanyl",
        "potassium"
    ]

    antibiotics = [
        "vancomycin",
        "cefepime",
        "ceftriaxone",
        "meropenem",
        "piperacillin",
        "azithromycin",
        "metronidazole"
    ]

    df["medication_name"] = df["medication_name"].fillna("").str.lower()
    df["route"] = df["route"].fillna("").str.lower()
    df["priority"] = df["priority"].fillna("").str.lower()
    df["risk_reasons"] = df["risk_reasons"].fillna("").str.lower()

    df["is_high_alert"] = df["medication_name"].apply(lambda x: contains_any(x, high_alert))
    df["is_antibiotic"] = df["medication_name"].apply(lambda x: contains_any(x, antibiotics))
    df["is_iv"] = df["route"].apply(lambda x: int("iv" in x or "intravenous" in x))
    df["is_stat"] = df["priority"].apply(lambda x: int(x == "stat"))
    df["missing_stop_time_flag"] = df["risk_reasons"].apply(lambda x: int("missing stop time" in x))

    features = [
        "is_high_alert",
        "is_antibiotic",
        "is_iv",
        "is_stat",
        "missing_stop_time_flag"
    ]

    X = df[features]
    y = df["risk_level"]

    if y.nunique() < 2:
        raise RuntimeError("Need at least two risk classes to train model.")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced"
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    print(classification_report(y_test, predictions))

    joblib.dump(
        {
            "model": model,
            "features": features
        },
        MODEL_PATH
    )

    print(f"Saved model to {MODEL_PATH}")


if __name__ == "__main__":
    main()