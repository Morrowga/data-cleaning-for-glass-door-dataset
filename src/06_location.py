"""Step 6 - Split Location and Headquarters into separate columns.

Location (where the job is):
    city, state (2-letter code), is_remote, location_level (city / state / country / remote)
Headquarters (where the company's main office is):
    hq_city, hq_state (US only), hq_country

Nothing is guessed. A value we do not understand stays empty and is listed in the report.
The original text columns are dropped (the raw CSV is still untouched).

Run from the doc-extraction-lab folder:
    python src/06_location.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "unclean" / "05_company_numbers.csv"
OUT = ROOT / "data" / "unclean" / "06_location_fixed.csv"
REPORT = ROOT / "results" / "06_location.txt"

STATES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
    "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
    "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX",
    "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY", "District of Columbia": "DC",
}
CODES = set(STATES.values())

lines: list[str] = []


def say(text: str = "") -> None:
    print(text)
    lines.append(text)


def parse_location(text):
    """-> (city, state, is_remote, level) or None if not understood."""
    if pd.isna(text):
        return (None, None, None, None)
    t = text.strip()
    if t.lower() == "remote":
        return (None, None, True, "remote")
    if t == "United States":
        return (None, None, False, "country")
    if t in STATES:
        return (None, STATES[t], False, "state")
    parts = [p.strip() for p in t.split(",")]
    if len(parts) >= 2 and parts[-1] in CODES:
        return (parts[0], parts[-1], False, "city")  # "Patuxent, Anne Arundel, MD": middle part is a county
    return None


def parse_hq(text):
    """-> (city, state, country) or None if not understood."""
    if pd.isna(text):
        return (None, None, None)
    parts = [p.strip() for p in text.strip().split(",")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    city, tail = parts
    if tail in CODES:
        return (city, tail, "United States")
    if tail.replace(" ", "").isalpha() and len(tail) > 2:  # a country name (may have spaces: United Kingdom)
        return (city, None, tail)
    return None  # "New York, 061", or a 2-letter code that is not a US state


df = pd.read_csv(SRC, dtype=str)
clean = df.copy()

# ---- Location ----
review = []
loc = []
for i, text in df["Location"].items():
    r = parse_location(text)
    if r is None:
        review.append((df.at[i, "index"], "Location", text))
        r = (None, None, None, None)
    loc.append(r)
clean["city"] = [r[0] for r in loc]
clean["state"] = [r[1] for r in loc]
clean["is_remote"] = pd.array([r[2] for r in loc], dtype="boolean")
clean["location_level"] = [r[3] for r in loc]

# ---- Headquarters ----
hq = []
for i, text in df["Headquarters"].items():
    r = parse_hq(text)
    if r is None:
        review.append((df.at[i, "index"], "Headquarters", text))
        r = (None, None, None)
    hq.append(r)
clean["hq_city"] = [r[0] for r in hq]
clean["hq_state"] = [r[1] for r in hq]
clean["hq_country"] = [r[2] for r in hq]

clean = clean.drop(columns=["Location", "Headquarters"])

# ---- checks ----
assert len(clean) == len(df), "row count changed"
assert "Location" not in clean.columns and "Headquarters" not in clean.columns
assert clean["state"].dropna().isin(CODES).all() and clean["hq_state"].dropna().isin(CODES).all()

say("STEP 6 - LOCATION AND HEADQUARTERS")
say(f"rows: {len(clean)}")
say()
say("Location level")
say(clean["location_level"].value_counts(dropna=False).to_string())
say(f"remote jobs: {int(clean['is_remote'].sum())}")
say()
say("Top 8 job states")
say(clean["state"].value_counts().head(8).to_string())
say()
say("Headquarters country")
say(clean["hq_country"].value_counts(dropna=False).to_string())
say()
say("Top 5 headquarters states")
say(clean["hq_state"].value_counts().head(5).to_string())

if review:
    say()
    say("NOT UNDERSTOOD (left empty, please look)")
    for idx, col, text in review:
        say(f"  index {idx:>4} {col:<13}{text!r}")

say()
say("check: row count same, every state code is a real US state, original text dropped")

clean.to_csv(OUT, index=False)
REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
say(f"saved -> {OUT.relative_to(ROOT)}")
