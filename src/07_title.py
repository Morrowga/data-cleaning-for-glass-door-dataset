"""Step 7 - Group the job titles into a family and a seniority level.

Rules only (no AI). The original Job Title is kept so every group can be checked.

title_family : data_scientist, data_engineer, data_analyst, ml_engineer, other
               (the ROLE only. Manager / Director / VP words are never used here, they go in seniority)
seniority    : director, manager, lead, senior, junior, mid, not_stated
               (not_stated = the title has no level word. We do NOT guess "mid".)

When a title fits more than one family, the first one in FAMILY_ORDER wins
and the title is listed in the report as ambiguous.

Run from the doc-extraction-lab folder:
    python src/07_title.py
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "unclean" / "06_location_fixed.csv"
OUT = ROOT / "data" / "unclean" / "07_title_grouped.csv"
REPORT = ROOT / "results" / "07_title.txt"

# ---------- family rules (checked on the lower-case title) ----------
NOT_OUR_FIELD = r"laborator"  # "Clinical Laboratory Scientist" is not a data job ("Clinical Data Analyst" is)
# "scientist" alone is too loose (lab scientist, toxicologist...), so it needs one of these data words too
DATA_WORD = r"data|machine learning|\bml\b|\bai\b|analytic|statistic|computational|decision|applied|deep learning"
FAMILY_RULES = {
    "ml_engineer": r"machine learning|\bml\b|\bai\b|deep learning",
    "data_scientist": r"scientist|data science",
    "data_engineer": r"engineer|developer|architect",
    "data_analyst": r"analyst|analytics",
}
FAMILY_ORDER = list(FAMILY_RULES)  # first match wins

# ---------- seniority rules (first match wins, top to bottom) ----------
WORD_LEVELS = [  # checked on the lower-case title
    ("director", r"\b(director|vp|vice president|head of|chief)\b"),
    ("manager", r"\bmanager\b"),
    ("lead", r"\b(lead|principal|staff)\b"),
    ("senior", r"\b(senior|sr)\b"),
    ("junior", r"\b(junior|jr|associate|entry|intern|internship|early career)\b"),
    ("mid", r"\bmid\b"),
]
NUMBER_LEVELS = [  # checked on the original title: "Analyst II", "Scientist 3"
    ("senior", r"\b(III|3)\b"),
    ("mid", r"\b(II|2)\b"),
    ("junior", r"\b(I|1)\b"),
]

lines: list[str] = []


def say(text: str = "") -> None:
    print(text)
    lines.append(text)


def families(title: str) -> list[str]:
    t = title.lower()
    if re.search(NOT_OUR_FIELD, t):
        return []
    hit = [f for f, p in FAMILY_RULES.items() if re.search(p, t)]
    for role in ("data_scientist", "data_engineer"):
        if role in hit and not re.search(DATA_WORD, t):
            hit.remove(role)  # a scientist or engineer without any data word: not a data job
    # a machine-learning word only makes an ml_engineer when it is not also a scientist/analyst title
    if "ml_engineer" in hit and ("data_scientist" in hit or "data_analyst" in hit):
        hit.remove("ml_engineer")
    elif "ml_engineer" in hit:
        hit = ["ml_engineer"]  # "Machine Learning Engineer" is one role, not a conflict with data_engineer
    return hit


def seniority(title: str) -> str:
    t = title.lower()
    for level, pattern in WORD_LEVELS:
        if re.search(pattern, t):
            return level
    for level, pattern in NUMBER_LEVELS:
        if re.search(pattern, title):
            return level
    return "not_stated"


df = pd.read_csv(SRC, dtype=str)
hits = df["Job Title"].map(families)

clean = df.copy()
clean["title_family"] = hits.map(lambda h: h[0] if h else "other")
clean["seniority"] = df["Job Title"].map(seniority)
ambiguous = hits.map(len) > 1

# ---- checks ----
assert len(clean) == len(df), "row count changed"
assert clean["title_family"].notna().all() and clean["seniority"].notna().all()
assert clean["Job Title"].equals(df["Job Title"]), "original title changed"
assert set(clean["title_family"]) <= set(FAMILY_ORDER) | {"other"}
assert "manager_director" not in set(clean["title_family"])

say("STEP 7 - JOB TITLES")
say(f"rows: {len(clean)}   distinct titles: {df['Job Title'].nunique()}")
say()
say("title_family")
say(clean["title_family"].value_counts().to_string())
say()
say("seniority")
say(clean["seniority"].value_counts().to_string())
say()
say("median salary_mid by family (rows with a family, USD per year)")
say(clean.assign(m=pd.to_numeric(clean["salary_mid"])).groupby("title_family")["m"].agg(["count", "median"]).round(0).to_string())

say()
say("SENSITIVITY: how much do the medians depend on the doubtful rows?")
say("  (all = every row of the family;  clear = without rows whose title fits 2+ families)")
m = pd.to_numeric(clean["salary_mid"])
say(f"  {'family':<16}{'rows':>6}{'clear rows':>12}{'median all':>13}{'median clear':>14}{'change':>9}")
for fam in FAMILY_ORDER + ["other"]:
    in_fam = clean["title_family"] == fam
    a, c = m[in_fam], m[in_fam & ~ambiguous]
    if len(a):
        say(f"  {fam:<16}{len(a):>6}{len(c):>12}{a.median():>13,.0f}{c.median():>14,.0f}{(c.median() - a.median()) / a.median():>9.1%}")
say(f"  share of rows in 'other': {(clean['title_family'] == 'other').mean():.1%}")

say()
say("DATA ENGINEER TITLES WITHOUT A DATA WORD (should now be empty)")
for title in sorted(set(clean.loc[(clean["title_family"] == "data_engineer") & ~clean["Job Title"].str.contains(DATA_WORD, case=False), "Job Title"])):
    say(f"  {title[:90]}")

say()
say("TITLES IN 'other' (please look)")
for title, n in clean.loc[clean["title_family"] == "other", "Job Title"].value_counts().items():
    say(f"  {n:>3}  {title[:90]}")

say()
say("AMBIGUOUS TITLES (fit more than one family, first rule won)")
for title in sorted(set(df.loc[ambiguous, "Job Title"])):
    fam = clean.loc[df["Job Title"] == title, "title_family"].iloc[0]
    say(f"  -> {fam:<16}{title[:80]}   (matched: {', '.join(families(title))})")

say()
say("SENIORITY CHECK: titles per level (not_stated is left out)")
for level in ["director", "manager", "lead", "senior", "junior", "mid"]:
    titles = sorted(set(clean.loc[clean["seniority"] == level, "Job Title"]))
    say(f"  [{level}] {len(titles)} titles")
    for title in titles:
        say(f"      {title[:90]}")

say()
say("check: row count same, original title kept, every row has a family and a level")

clean.to_csv(OUT, index=False)
REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
say(f"saved -> {OUT.relative_to(ROOT)}")
