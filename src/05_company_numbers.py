"""Step 5 - Turn Size, Revenue and Founded into numbers.

Size     "1001 to 5000 employees" -> size_min 1001, size_max 5000
         "10000+ employees"       -> size_min 10000, size_max empty (no upper limit)
Revenue  "$100 to $500 million (USD)" -> revenue_min 100000000, revenue_max 500000000
         "Less than $1 million (USD)" -> revenue_min empty, revenue_max 1000000
Founded  "1993" -> 1993 (whole number), and company_age = SCRAPE_YEAR - founded

The original Size and Revenue text is kept as a display label.

Run from the doc-extraction-lab folder:
    python src/05_company_numbers.py
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "unclean" / "04_salary_fixed.csv"
OUT = ROOT / "data" / "unclean" / "05_company_numbers.csv"
REPORT = ROOT / "results" / "05_company_numbers.txt"

SCRAPE_YEAR = 2020  # job texts mention 2020 most, and the newest company was founded in 2019
UNIT = {"million": 1_000_000, "billion": 1_000_000_000}

lines: list[str] = []


def say(text: str = "") -> None:
    print(text)
    lines.append(text)


def parse_size(text):
    """-> (min, max) as numbers or None. Returns False when the text is not understood."""
    if pd.isna(text):
        return (None, None)
    t = text.strip()
    if m := re.fullmatch(r"(\d+) to (\d+) employees", t):
        return (int(m[1]), int(m[2]))
    if m := re.fullmatch(r"(\d+)\+ employees", t):
        return (int(m[1]), None)
    return False


def parse_revenue(text):
    if pd.isna(text):
        return (None, None)
    t = text.strip()
    # $100 to $500 million (USD)   |   $500 million to $1 billion (USD)
    if m := re.fullmatch(r"\$(\d+)(?: (million|billion))? to \$(\d+) (million|billion) \(USD\)", t):
        hi_unit = UNIT[m[4]]
        lo_unit = UNIT[m[2]] if m[2] else hi_unit
        return (int(m[1]) * lo_unit, int(m[3]) * hi_unit)
    if m := re.fullmatch(r"\$(\d+)\+ (million|billion) \(USD\)", t):
        return (int(m[1]) * UNIT[m[2]], None)
    if m := re.fullmatch(r"Less than \$(\d+) (million|billion) \(USD\)", t):
        return (None, int(m[1]) * UNIT[m[2]])
    return False


df = pd.read_csv(SRC, dtype=str)
clean = df.copy()

# ---- Size and Revenue ----
problems = []
for col, parse, lo, hi in [("Size", parse_size, "size_min", "size_max"), ("Revenue", parse_revenue, "revenue_min", "revenue_max")]:
    results = df[col].map(parse)
    for i, r in results.items():
        if r is False:
            problems.append((df.at[i, "index"], col, df.at[i, col]))
    pairs = results.map(lambda r: r if r is not False else (None, None))
    clean[lo] = pd.array([p[0] for p in pairs], dtype="Int64")
    clean[hi] = pd.array([p[1] for p in pairs], dtype="Int64")

# ---- Founded and company age ----
clean["Founded"] = pd.to_numeric(df["Founded"]).astype("Int64")
clean["company_age"] = (SCRAPE_YEAR - clean["Founded"]).astype("Int64")

# ---- checks ----
assert len(clean) == len(df), "row count changed"
both = clean["size_min"].notna() & clean["size_max"].notna()
assert (clean.loc[both, "size_min"] <= clean.loc[both, "size_max"]).all(), "size min above max"
both = clean["revenue_min"].notna() & clean["revenue_max"].notna()
assert (clean.loc[both, "revenue_min"] <= clean.loc[both, "revenue_max"]).all(), "revenue min above max"
bad_year = clean["Founded"].notna() & ((clean["Founded"] < 1700) | (clean["Founded"] > SCRAPE_YEAR))
assert not bad_year.any(), "a founded year is not realistic"

say("STEP 5 - SIZE, REVENUE, FOUNDED")
say(f"rows: {len(clean)}      reference year for company_age: {SCRAPE_YEAR}")
say()
say(f"{'column':<14}{'filled':>8}{'empty':>8}")
for col in ["size_min", "size_max", "revenue_min", "revenue_max", "Founded", "company_age"]:
    say(f"{col:<14}{int(clean[col].notna().sum()):>8}{int(clean[col].isna().sum()):>8}")
say()
say("open ended (one side stays empty on purpose)")
say(f"  size    '10000+ employees'     : {int(clean['size_max'].isna().sum() - clean['Size'].isna().sum())}")
say(f"  revenue open ended (top or bottom): {int((clean['revenue_min'].isna() ^ clean['revenue_max'].isna()).sum())}")
say()
say("company_age (years)")
say(clean["company_age"].astype("float").describe().loc[["min", "50%", "max"]].round(0).to_string())
say()
say("distinct ranges read")
say(clean[["Size", "size_min", "size_max"]].drop_duplicates().dropna(subset=["Size"]).sort_values("size_min").to_string(index=False))
say()
say(clean[["Revenue", "revenue_min", "revenue_max"]].drop_duplicates().dropna(subset=["Revenue"]).sort_values(["revenue_min", "revenue_max"]).to_string(index=False))

if problems:
    say()
    say("NOT UNDERSTOOD (left empty)")
    for p in problems:
        say(f"  index {p[0]} {p[1]}: {p[2]!r}")

say()
say("check: row count same, min <= max, founded year realistic")

clean.to_csv(OUT, index=False)
REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
say(f"saved -> {OUT.relative_to(ROOT)}")
