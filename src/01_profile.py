"""Step 1 - Profile the raw data. Nothing is changed, we only look.

Run from the doc-extraction-lab folder:
    python src/01_profile.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "Uncleaned_DS_jobs.csv"
OUT = ROOT / "results" / "01_profile.txt"

# This file does not use blank cells for "missing". It uses these values.
MISSING = {"-1", "-1.0", "Unknown", "Unknown / Non-Applicable", "N/A", ""}

# Same job posted again = same title + company + location
DUP_KEYS = ["Job Title", "Company Name", "Location"]

lines: list[str] = []


def say(text: str = "") -> None:
    print(text)
    lines.append(text)


# dtype=str: read everything as text so nothing is changed by pandas yet
df = pd.read_csv(CSV, dtype=str, keep_default_na=False)

say("STEP 1 - PROFILE")
say(f"file   : {CSV.name}")
say(f"rows   : {len(df)}")
say(f"columns: {df.shape[1]}")

# ---- missing values per column ----
say()
say("MISSING VALUES (counting -1, Unknown, N/A and blanks)")
say(f"{'column':<20}{'missing':>8}{'percent':>9}{'unique':>8}  example")
rows = []
for col in df.columns:
    values = df[col].str.strip()
    missing = int(values.isin(MISSING).sum())
    rows.append((col, missing, 100 * missing / len(df), values.nunique(), values.iloc[0][:40].replace("\n", " ")))
for col, missing, pct, unique, example in sorted(rows, key=lambda r: -r[1]):
    say(f"{col:<20}{missing:>8}{pct:>8.1f}%{unique:>8}  {example}")

# ---- duplicates ----
say()
say("DUPLICATES")
say(f"same {' + '.join(DUP_KEYS)}: {int(df.duplicated(subset=DUP_KEYS).sum())} repeated rows")
say(f"same Job Description          : {int(df.duplicated(subset=['Job Description']).sum())} repeated rows")
say(f"completely identical rows (ignoring the index column): {int(df.drop(columns=['index']).duplicated().sum())}")

# ---- shape of the text columns ----
say()
say("TEXT LENGTH")
length = df["Job Description"].str.len()
say(f"Job Description  min {length.min()}  median {int(length.median())}  max {length.max()}")

# ---- glued values and odd formats, the things later steps will fix ----
say()
say("THINGS LATER STEPS WILL FIX")
say(f"Company Name has the rating glued on (contains a new line): {int(df['Company Name'].str.contains(chr(10)).sum())}")
say(f"Salary has 'Employer Provided'                            : {int(df['Salary Estimate'].str.contains('Employer').sum())}")
say(f"Location without a comma (Remote, a state, a country)      : {int((~df['Location'].str.contains(',')).sum())}")
say(f"Distinct job titles                                        : {df['Job Title'].nunique()}")

OUT.parent.mkdir(exist_ok=True)
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\nsaved -> {OUT.relative_to(ROOT)}")
