

"""Load the raw income-statement CSV with explicit types, after verifying its fingerprint.

Run from the project root:  python -m src.data_load
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()  # reads .env so paths come from settings, not hard-coded

RAW_PATH = Path(os.getenv("DATA_RAW_PATH", "data/raw/corporate_income_statement.csv"))
EXPECTED_SHA256 = "0898c7c5095a153b3d829ecfd788533722417a706a7f31adb23121842561da30"
KEY_COLS = ["symbol", "fiscalDateEnding"]          # the grain: one row per company per quarter
TEXT_COLS = ["symbol", "reportedCurrency"]
DATE_COLS = ["fiscalDateEnding"]


def sha256_of(path: Path) -> str:
    """Return the SHA-256 fingerprint of a file, read in 64 KB chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_raw(path: Path = RAW_PATH, verify: bool = True) -> pd.DataFrame:
    """Read the CSV exactly as delivered: 'None' and blanks become missing, nothing else does."""
    if verify:
        actual = sha256_of(path)
        if actual != EXPECTED_SHA256:
            raise ValueError(f"Fingerprint mismatch: expected {EXPECTED_SHA256}, got {actual}")
    df = pd.read_csv(
        path,
        na_values=["None", ""],
        keep_default_na=False,          # a ticker like "NA" must never turn into a missing value
        dtype={col: "str" for col in TEXT_COLS},
        parse_dates=DATE_COLS,
    )
    numeric_cols = [c for c in df.columns if c not in TEXT_COLS + DATE_COLS]
    df[numeric_cols] = df[numeric_cols].astype("float64")
    return df


if __name__ == "__main__":
    df = load_raw()
    print(f"Fingerprint OK  : {EXPECTED_SHA256[:16]}...")
    print(f"Shape           : {df.shape[0]} rows x {df.shape[1]} columns")
    print(f"Dtypes          : {df.dtypes.astype(str).value_counts().to_dict()}")
    print(f"Grain unique    : {not df.duplicated(KEY_COLS).any()}  (symbol + fiscalDateEnding)")
    print(f"Companies       : {df['symbol'].nunique()}")
    print(f"Date range      : {df['fiscalDateEnding'].min().date()} to {df['fiscalDateEnding'].max().date()}")
    per_co = df.groupby("symbol").size()
    print(f"Rows per company: min {per_co.min()} ({per_co.idxmin()}), max {per_co.max()}")