"""Step 4 - Turn Salary Estimate (text) into numbers.

"$137K-$171K (Glassdoor est.)"  ->  salary_min 137000, salary_max 171000,
                                    salary_mid 154000, salary_source glassdoor_est

The original text column is dropped (the raw CSV is still untouched).

Run from the doc-extraction-lab folder:
    python src/04_salary.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "unclean" / "03_company_fixed.csv"
OUT = ROOT / "data" / "unclean" / "04_salary_fixed.csv"
REPORT = ROOT / "results" / "04_salary.txt"

# $137K-$171K (Glassdoor est.)   or   $145K-$225K(Employer est.)  (no space before the bracket)
PATTERN = r"^\s*\$(\d+)K\s*-\s*\$(\d+)K\s*\(\s*(Glassdoor|Employer) est\.\s*\)\s*$"
SOURCE = {"Glassdoor": "glassdoor_est", "Employer": "employer_est"}
LOW, HIGH = 10_000, 500_000  # a yearly salary outside this range is suspicious

lines: list[str] = []


def say(text: str = "") -> None:
    print(text)
    lines.append(text)


df = pd.read_csv(SRC, dtype=str)

found = df["Salary Estimate"].str.extract(PATTERN)
found.columns = ["lo", "hi", "who"]
readable = found["lo"].notna()

clean = df.copy()
clean["salary_min"] = (pd.to_numeric(found["lo"]) * 1000).astype("Int64")
clean["salary_max"] = (pd.to_numeric(found["hi"]) * 1000).astype("Int64")
clean["salary_mid"] = ((clean["salary_min"] + clean["salary_max"]) / 2).astype("Int64")
clean["salary_source"] = found["who"].map(SOURCE)
clean = clean.drop(columns=["Salary Estimate"])

# ---- checks ----
bad_order = readable & (clean["salary_min"] > clean["salary_max"])
out_of_range = readable & ((clean["salary_min"] < LOW) | (clean["salary_max"] > HIGH))
assert len(clean) == len(df), "row count changed"
assert "Salary Estimate" not in clean.columns

say("STEP 4 - SALARY")
say(f"rows                              : {len(clean)}")
say(f"salary read                       : {int(readable.sum())}")
say(f"salary NOT readable (left empty)  : {int((~readable).sum())}")
say(f"min above max                     : {int(bad_order.sum())}")
say(f"outside ${LOW:,} - ${HIGH:,}        : {int(out_of_range.sum())}")
say()
say("by source")
say(clean["salary_source"].value_counts(dropna=False).to_string())
say()
say("numbers (USD per year)")
say(clean[["salary_min", "salary_max", "salary_mid"]].astype("float").describe().loc[["min", "50%", "max"]].round(0).to_string())

problems = df.index[~readable | bad_order | out_of_range]
if len(problems):
    say()
    say("ROWS TO REVIEW")
    for i in problems:
        say(f"  index {df.at[i, 'index']}: {df.at[i, 'Salary Estimate']!r}")

say()
say("check: row count same, text column dropped, min <= max")

clean.to_csv(OUT, index=False)
REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
say(f"saved -> {OUT.relative_to(ROOT)}")
