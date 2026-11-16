"""Step 9a - Rules baseline: skills, years of experience and degree from the job description.

No AI here. Plain word lists and patterns. This is the baseline that the AI result (9b)
will be compared with. New columns are named *_rules so the AI columns can sit next to them.

    skills_rules      skills found, joined with "|"   (from a fixed list)
    skill_count_rules how many skills were found
    min_years_rules   first "N years" mentioned next to the word "experience" (empty if none)
    years_unclear     True if the description names 2+ different year numbers (rules cannot pick)
    degree_rules      lowest degree mentioned: bachelor / master / phd / not_stated

Run from the doc-extraction-lab folder:
    python src/09a_rules.py
"""
import re
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "unclean" / "08_deduplicated.csv"
OUT = ROOT / "data" / "unclean" / "09a_rules.csv"
REPORT = ROOT / "results" / "09a_rules.txt"

# ---------- skills: name -> pattern (case-insensitive unless the name is in CASE_SENSITIVE) ----------
SKILLS = {
    "Python": r"\bpython\b",
    "SQL": r"\bsql\b|mysql|postgres",
    "R": r"(?<![A-Za-z&/])R(?![A-Za-z&])",  # the language R, not "R&D"
    "Java": r"\bjava\b",
    "Scala": r"\bscala\b",
    "C++": r"c\+\+",
    "SAS": r"\bsas\b",
    "MATLAB": r"matlab",
    "Spark": r"\bspark\b|pyspark",
    "Hadoop": r"hadoop",
    "Hive": r"\bhive\b",
    "Kafka": r"kafka",
    "Airflow": r"airflow",
    "Snowflake": r"snowflake",
    "AWS": r"\baws\b|amazon web services",
    "Azure": r"\bazure\b",
    "GCP": r"\bgcp\b|google cloud",
    "Docker": r"docker",
    "Kubernetes": r"kubernetes",
    "Git": r"\bgit\b|github",
    "TensorFlow": r"tensorflow",
    "PyTorch": r"pytorch",
    "Keras": r"keras",
    "Scikit-learn": r"scikit|sklearn",
    "Pandas": r"\bpandas\b",
    "NumPy": r"numpy",
    "NLP": r"\bnlp\b|natural language",
    "Deep learning": r"deep learning",
    "Machine learning": r"machine learning",
    "Statistics": r"statistic",
    "Tableau": r"tableau",
    "Power BI": r"power ?bi",
    "Excel": r"\bexcel\b",
}
CASE_SENSITIVE = {"R"}

# ---------- years of experience ----------
YEARS = re.compile(r"(\d{1,2})\s*(?:\+|\s*-\s*\d{1,2}|\s*to\s*\d{1,2}|\s*or more)?\s*\+?\s*(?:years?|yrs?)\b", re.I)
NEAR = 90  # the word "experience" must be this close to the number

# ---------- degree ----------
DEGREES = [  # lowest first. (?i:...) = ignore case only for the full words; abbreviations must be capitals
    ("bachelor", r"(?i:bachelor)|\bB\.S\.|\bBS\b|\bBSc\b|\bB\.A\.|\bBA\b"),
    ("master", r"(?i:master)|\bM\.S\.|\bMS\b(?! (?:Office|Excel|Word|Access|SQL|Project|Azure|Dynamics))|\bMSc\b|\bMBA\b"),
    ("phd", r"(?i:ph\.?d|doctorate|doctoral)"),
]

lines: list[str] = []


def say(text: str = "") -> None:
    print(text)
    lines.append(text)


def find_skills(text: str) -> list[str]:
    found = []
    for name, pattern in SKILLS.items():
        flags = 0 if name in CASE_SENSITIVE else re.I
        if re.search(pattern, text, flags):
            found.append(name)
    return found


def find_years(text: str) -> list[int]:
    numbers = []
    for m in YEARS.finditer(text):
        n = int(m.group(1))
        if not 1 <= n <= 20:  # "50 years in business" is not a requirement
            continue
        around = text[max(0, m.start() - NEAR): m.end() + NEAR].lower()
        if "experience" in around or " exp" in around:
            numbers.append(n)
    return numbers


def find_degree(text: str) -> str:
    for level, pattern in DEGREES:
        if re.search(pattern, text):
            return level
    return "not_stated"


df = pd.read_csv(SRC, dtype=str)
text = df["Job Description"].fillna("")

skills = text.map(find_skills)
years = text.map(find_years)

clean = df.copy()
clean["skills_rules"] = skills.map("|".join).replace("", pd.NA)
clean["skill_count_rules"] = skills.map(len)
clean["min_years_rules"] = pd.array([y[0] if y else None for y in years], dtype="Int64")
clean["years_unclear"] = years.map(lambda y: len(set(y)) > 1)
clean["degree_rules"] = text.map(find_degree)

# ---- checks ----
assert len(clean) == len(df), "row count changed"
assert clean["degree_rules"].isin(["bachelor", "master", "phd", "not_stated"]).all()
assert clean["min_years_rules"].dropna().between(1, 20).all()

say("STEP 9a - RULES BASELINE")
say(f"rows: {len(clean)}")
say()
say("skills found (rows containing each skill)")
counts = Counter(s for row in skills for s in row)
for name, n in counts.most_common():
    say(f"  {name:<18}{n:>5}  {n / len(clean):>6.1%}")
say(f"rows with no skill found : {int((clean['skill_count_rules'] == 0).sum())}")
say(f"skills per row           : median {int(clean['skill_count_rules'].median())}, max {int(clean['skill_count_rules'].max())}")
say()
say("years of experience")
say(f"  read from the text        : {int(clean['min_years_rules'].notna().sum())}")
say(f"  not found                 : {int(clean['min_years_rules'].isna().sum())}")
say(f"  2+ different numbers (rules cannot choose, AI may do better): {int(clean['years_unclear'].sum())}")
say(clean["min_years_rules"].value_counts().sort_index().to_string())
say()
say("degree (lowest degree mentioned)")
say(clean["degree_rules"].value_counts().to_string())

say()
say("CASES THE RULES CANNOT READ WELL (where the AI should help)")
say("  - years written as words: 'five years', 'three to five years'")
say("  - 'bachelor preferred' vs 'bachelor required' (the rules ignore required/preferred)")
say("  - 'or equivalent experience' instead of a degree")
words = text.str.contains(r"\b(?:one|two|three|four|five|six|seven|eight|ten)\s+(?:\(\d+\)\s*)?(?:\+\s*)?years", case=False)
say(f"  rows that write years as a word and have no number found: {int((words & clean['min_years_rules'].isna()).sum())}")
equiv = text.str.contains(r"equivalent (?:work |practical |professional )?experience", case=False)
say(f"  rows that say 'equivalent experience' : {int(equiv.sum())}")

say()
say("check: row count same, degree values valid, years between 1 and 20")

clean.to_csv(OUT, index=False)
REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
say(f"saved -> {OUT.relative_to(ROOT)}")
