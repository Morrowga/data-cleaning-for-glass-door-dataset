"""Step 11 - Save the final files into the final/ folder.

    clean.csv               the tidy table (no long text), readable column names, sensible order
    descriptions.csv        index + the long job description (join with clean.csv on `index`)
    unclean_sample.csv      20 random rows of the RAW file (the "before" side of the story)
    extraction_audit.csv    rules answer and AI answer side by side for skills / years / degree
    removed_duplicates.csv  the 13 exact copies removed in step 8
    change_log.md           what each step did to which column

Nothing is deleted. Run from the doc-extraction-lab folder:
    python src/11_finalize.py
"""
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "Uncleaned_DS_jobs.csv"
UNCLEAN = ROOT / "data" / "unclean"
FINAL = ROOT / "final"
FINAL.mkdir(exist_ok=True)

df = pd.read_csv(UNCLEAN / "09d_final_fields.csv", dtype=str)

# ---------- readable names ----------
RENAME = {
    "Job Title": "job_title", "Company Name": "company", "Rating": "rating", "Type of ownership": "ownership",
    "Industry": "industry", "Sector": "sector", "Size": "size_label", "Revenue": "revenue_label", "Founded": "founded",
}
df = df.rename(columns=RENAME)

ORDER = [
    "index", "job_title", "title_family", "seniority",
    "company", "rating", "ownership", "industry", "sector",
    "size_label", "size_min", "size_max", "revenue_label", "revenue_min", "revenue_max", "founded", "company_age",
    "hq_city", "hq_state", "hq_country",
    "city", "state", "is_remote", "location_level",
    "salary_min", "salary_max", "salary_mid", "salary_source",
    "skills", "skill_count", "min_years", "years_evidence", "degree_required",
    "repeat_group_size", "possible_repeat",
]
left_out = set(df.columns) - set(ORDER) - {"Job Description"}
assert not left_out, f"columns not placed anywhere: {left_out}"
assert set(ORDER) <= set(df.columns), "a listed column does not exist"

clean = df[ORDER]
descriptions = df[["index", "Job Description"]].rename(columns={"Job Description": "description"})

clean.to_csv(FINAL / "clean.csv", index=False)
descriptions.to_csv(FINAL / "descriptions.csv", index=False)

# ---------- the "before" sample: raw rows, untouched ----------
raw = pd.read_csv(RAW, dtype=str, keep_default_na=False)
raw.sample(20, random_state=3).sort_values("index", key=lambda s: s.astype(int)).to_csv(FINAL / "unclean_sample.csv", index=False)

shutil.copy(UNCLEAN / "09d_extraction_audit.csv", FINAL / "extraction_audit.csv")
shutil.copy(UNCLEAN / "08_removed_duplicates.csv", FINAL / "removed_duplicates.csv")

# ---------- change log ----------
LOG = [
    # raw column, final column(s), step, what happened
    ("index", "index", "-", "kept as the row number"),
    ("Job Title", "job_title, title_family, seniority", "7", "title kept; role and level added from word rules"),
    ("Salary Estimate", "salary_min, salary_max, salary_mid, salary_source", "4", "text turned into numbers; original text dropped"),
    ("Job Description", "descriptions.csv; skills, skill_count, min_years, years_evidence, degree_required", "9", "long text moved to its own file; three facts extracted from it"),
    ("Rating", "rating", "3", "kept; -1 became empty (step 2); not changed in step 3"),
    ("Company Name", "company", "3", "glued rating removed"),
    ("Location", "city, state, is_remote, location_level", "6", "split; original text dropped"),
    ("Headquarters", "hq_city, hq_state, hq_country", "6", "split; original text dropped"),
    ("Size", "size_label, size_min, size_max", "5", "range read into numbers; label kept"),
    ("Founded", "founded, company_age", "5", "whole number; age = 2020 - founded"),
    ("Type of ownership", "ownership", "2", "-1 / Unknown became empty"),
    ("Industry", "industry", "2", "-1 became empty"),
    ("Sector", "sector", "2", "-1 became empty"),
    ("Revenue", "revenue_label, revenue_min, revenue_max", "5", "range read into numbers (USD); label kept"),
    ("Competitors", "(dropped)", "2", "74.6% empty and a list inside one cell"),
    ("(new)", "repeat_group_size, possible_repeat", "8", "flags for jobs seen more than once with different salaries"),
]
rows_before, rows_after = len(raw), len(clean)
log = ["# Change log", "",
       f"Raw file: `Uncleaned_DS_jobs.csv`, {rows_before} rows, {raw.shape[1]} columns.",
       f"Final file: `final/clean.csv`, {rows_after} rows, {clean.shape[1]} columns (+ `descriptions.csv`).", "",
       "| raw column | final column(s) | step | what happened |", "|---|---|---|---|"]
log += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in LOG]
log += ["", "## Rows", "",
        f"- {rows_before} raw rows",
        f"- 13 exact copies removed in step 8 (`removed_duplicates.csv`) -> {rows_after} rows",
        "- Salary variants of the same job were kept and flagged (`possible_repeat`).", "",
        "## Rule of the project", "",
        "Code first, AI only where code cannot do it, and every step checks itself. The raw file is never edited.", ""]
(FINAL / "change_log.md").write_text("\n".join(log), encoding="utf-8")

# ---------- checks ----------
check = pd.read_csv(FINAL / "clean.csv", dtype=str)
assert len(check) == len(descriptions) == rows_after == 659
assert check["index"].is_unique and (check["index"].values == descriptions["index"].values).all()

print("STEP 11 - FINAL FILES")
print(f"clean.csv      {len(clean)} rows x {clean.shape[1]} columns")
for f in sorted(FINAL.iterdir()):
    print(f"  {f.name:<24}{f.stat().st_size / 1024:>9,.0f} KB")
print("check: same rows in clean and descriptions, index unique, every column placed")
(ROOT / "results" / "11_finalize.txt").write_text(f"clean.csv {len(clean)} rows x {clean.shape[1]} columns\n", encoding="utf-8")
