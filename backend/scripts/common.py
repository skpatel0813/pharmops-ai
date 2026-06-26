from pathlib import Path
import pandas as pd
import re
from app.config import RAW_DATA_DIR


def find_file(name_contains: str):
    patterns = [
        f"**/*{name_contains}*.csv",
        f"**/*{name_contains}*.csv.gz"
    ]

    matches = []

    for pattern in patterns:
        matches.extend(list(RAW_DATA_DIR.glob(pattern)))

    if not matches:
        return None

    matches = sorted(matches, key=lambda p: len(str(p)))
    return matches[0]


def read_csv_flexible(path: Path):
    if path is None:
        return None

    return pd.read_csv(path, compression="infer", low_memory=False)


def clean_id(value, prefix: str | None = None):
    if pd.isna(value):
        return None

    try:
        if float(value).is_integer():
            value = int(float(value))
    except Exception:
        pass

    value = str(value)

    if prefix:
        return f"{prefix}-{value}"

    return value


def safe_datetime(series):
    return pd.to_datetime(series, errors="coerce")


def normalize_text(value):
    if pd.isna(value):
        return ""

    value = str(value).lower().strip()
    value = re.sub(r"[^a-z0-9\s\-\/]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value


def med_tokens(name: str):
    cleaned = normalize_text(name)
    return set(token for token in cleaned.split() if len(token) >= 4)