"""Step 2 - Turn fake "missing" values into real empty values.

-1, Unknown, Unknown / Non-Applicable and N/A all mean "no data".
We replace them with one real empty value (NaN), and drop the Competitors column.

Run from the doc-extraction-lab folder:
    python src/02_missing.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "Uncleaned_DS_jobs.csv"
OUT = ROOT / "data" / "unclean" / "02_missing_fixed.csv"
REPORT = ROOT / "results" / "02_missing.txt"

# A cell is "missing" only when the WHOLE cell is one of these.
PLACEHOLDERS = {"-1", "-1.0", "Unknown", "Unknown / Non-Applicable", "N/A", ""}
DROP = ["Competitors"]  # 74.6% empty and a list inside one cell

lines: list[str] = []


def say(text: str = "") -> None:
    print(text)
    lines.append(text)


df = pd.read_csv(CSV, dtype=str, keep_default_na=False)
before_missing = {c: int(df[c].str.strip().isin(PLACEHOLDERS).sum()) for c in df.columns}

# ---- replace placeholders with a real empty value ----
clean = df.copy()
for col in clean.columns:
    clean[col] = clean[col].where(~clean[col].str.strip().isin(PLACEHOLDERS), pd.NA)
clean = clean.drop(columns=DROP)

# ---- prove that nothing else changed ----
for col in clean.columns:
    still_there = ~clean[col].isna()
    assert (clean.loc[still_there, col] == df.loc[still_there, col]).all(), f"{col}: a real value changed"
    assert int(clean[col].isna().sum()) == before_missing[col], f"{col}: missing count is different"
assert len(clean) == len(df), "row count changed"

say("STEP 2 - MISSING VALUES")
say(f"rows   : {len(clean)}")
say(f"columns: {df.shape[1]} -> {clean.shape[1]}  (dropped: {', '.join(DROP)})")
say()
say(f"{'column':<20}{'placeholders before':>20}{'empty after':>13}")
for col in clean.columns:
    say(f"{col:<20}{before_missing[col]:>20}{int(clean[col].isna().sum()):>13}")
say()
say("check: every real value is unchanged, and every placeholder is now empty")

OUT.parent.mkdir(parents=True, exist_ok=True)
clean.to_csv(OUT, index=False)
REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
say(f"saved -> {OUT.relative_to(ROOT)}")
