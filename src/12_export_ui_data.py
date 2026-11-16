"""Step 12 - Export the data the portfolio screen needs (UI-1).

Every number and every example is computed from the real files, nothing is typed in by hand.
Only the explanation texts (why / rule / check) are written here.

Output folder (default: ../public/lab/data-cleaning inside the portfolio):
    lab-data.json         steps, numbers, examples, scores, preview rows   (the screen reads this)
    clean.csv             copy of final/clean.csv                          (download link)
    unclean_sample.csv    copy of final/unclean_sample.csv                 (download link)

If this folder is moved out of the portfolio, pass the output folder:
    python src/12_export_ui_data.py --out /path/to/portfolio/public/lab/data-cleaning
"""
import argparse
import json
import re
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "final"
RAW = ROOT / "Uncleaned_DS_jobs.csv"
RESULTS = ROOT / "results"
SOURCE_URL = "https://www.kaggle.com/datasets/rashikrahmanpritom/data-science-job-posting-on-glassdoor?select=Uncleaned_DS_jobs.csv"
PLACEHOLDERS = {"-1", "-1.0", "Unknown", "Unknown / Non-Applicable", "N/A", ""}

parser = argparse.ArgumentParser()
parser.add_argument("--out", default=str(ROOT.parent / "public" / "lab" / "data-cleaning"))
OUT = Path(parser.parse_args().out)

raw = pd.read_csv(RAW, dtype=str, keep_default_na=False)
clean = pd.read_csv(FINAL / "clean.csv", dtype=str)
desc = pd.read_csv(FINAL / "descriptions.csv", dtype=str).set_index("index")["description"]
removed = pd.read_csv(FINAL / "removed_duplicates.csv", dtype=str)
audit = pd.read_csv(FINAL / "extraction_audit.csv", dtype=str)
ai = pd.read_csv(ROOT / "data" / "unclean" / "09b_ai_claude-haiku-5-5.csv", dtype=str)
scores = json.loads((RESULTS / "09c_score.json").read_text(encoding="utf-8"))
validate_txt = (RESULTS / "10_validate.txt").read_text(encoding="utf-8")
review = pd.read_csv(RESULTS / "10_review.csv", dtype=str)

UNCLEAN = ROOT / "data" / "unclean"
st4 = pd.read_csv(UNCLEAN / "04_salary_fixed.csv", dtype=str)
st5 = pd.read_csv(UNCLEAN / "05_company_numbers.csv", dtype=str)
st6 = pd.read_csv(UNCLEAN / "06_location_fixed.csv", dtype=str)
st7 = pd.read_csv(UNCLEAN / "07_title_grouped.csv", dtype=str)
raw_i = raw.set_index("index")
clean_i = clean.set_index("index")


def val(x):
    """A JSON friendly value: empty becomes null."""
    return None if x is None or (isinstance(x, float) and pd.isna(x)) or x == "" or pd.isna(x) else x


def num(label, value):
    return {"label": label, "value": value}


def fmt(n) -> str:
    return f"{int(n):,}"


def cut(text, n):
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def ex(field, before, after):
    return {"field": field, "before": before, "after": after}


# ---------- numbers computed from the data ----------
n_raw, n_clean = len(raw), len(clean)
missing = {c: int(raw[c].str.strip().isin(PLACEHOLDERS).sum()) for c in raw.columns if c != "index"}
top_missing = sorted(missing.items(), key=lambda kv: -kv[1])[:5]
dup_raw = int(raw.duplicated(subset=["Job Title", "Company Name", "Location"]).sum())
glued = raw["Company Name"].str.contains("\n")
glued_rating = raw.loc[glued, "Company Name"].str.split("\n", n=1).str[1].str.strip()
glued_mismatch = int((glued_rating != raw.loc[glued, "Rating"]).sum())
mid = pd.to_numeric(st4["salary_mid"])
sizes_open = int((st5["size_min"].notna() & st5["size_max"].isna()).sum())
revenue_open = int((st5["revenue_min"].isna() ^ st5["revenue_max"].isna()).sum())
age = pd.to_numeric(st5["company_age"])
hq_us = int((st6["hq_country"] == "United States").sum())
hq_foreign = int((st6["hq_country"].notna() & (st6["hq_country"] != "United States")).sum())
families = st7["title_family"].value_counts()
companies_before = raw["Company Name"].str.split("\n").str[0].nunique()
companies_after = clean["company"].nunique()
flagged = int((clean["possible_repeat"] == "True").sum())
biggest = int(pd.to_numeric(clean["repeat_group_size"]).max())
years_found = int(clean["min_years"].notna().sum())
ai_cost = float(pd.to_numeric(ai["cost_usd"]).sum())
ai_repairs = int((pd.to_numeric(ai["ai_attempts"]) > 1).sum())
check_lines = re.search(r"failed\n(.*?)\n\n", validate_txt, re.S).group(1).strip().splitlines()
n_checks = len(check_lines)
suspicious = {k.strip(): int(v) for k, v in re.findall(r"^\s+(.+?)\s*:\s*(\d+)\s*$", validate_txt.split("SUSPICIOUS")[1], re.M)}


# ---------- pick real example rows ----------
def first_index(mask):
    return raw.loc[mask, "index"].iloc[0]


i_main = "0"
i_missing = first_index((raw["Rating"] == "-1") & (raw["Founded"] == "-1"))
i_open = first_index((raw["Size"] == "10000+ employees") & (raw["Revenue"] == "$10+ billion (USD)"))
i_remote = first_index(raw["Location"] == "Remote")
i_foreign = clean.loc[clean["hq_country"].notna() & (clean["hq_country"] != "United States"), "index"].iloc[0]
title_rows = {t: clean.loc[clean["job_title"] == t, "index"].iloc[0] for t in ["Sr. Data Scientist II", "Data Science Manager", "Machine Learning Engineer, Sr."] if (clean["job_title"] == t).any()}
hatch = removed[removed["Company Name"].str.contains("Hatch Data")]
i_hatch = clean.loc[clean["company"] == "Hatch Data Inc", "index"].iloc[0]

# the extraction example: a row with years from the AI, skills and a degree
cand = clean[clean["min_years"].notna() & clean["skills"].notna() & (clean["degree_required"] != "not_stated")]
i_extract = "1" if "1" in set(cand["index"]) else cand["index"].iloc[0]
quote = clean_i.at[i_extract, "years_evidence"]
text = desc.at[i_extract]
m = re.search(r"\s+".join(re.escape(w) for w in str(quote).split()), text, re.I)
def whole_words(chunk: str) -> str:
    chunk = " ".join(chunk.split())
    return "…" + chunk.split(" ", 1)[1] if " " in chunk else chunk


excerpt = (whole_words(text[max(0, m.start() - 90): m.start()]) + " " + " ".join(text[m.start(): m.end() + 90].split()[:-1])) if m else cut(text, 230)
r = clean_i.loc[i_extract]

steps = [
    {"id": "profile", "step": 1, "group": "file", "title": "Look at the file", "tool": "Python + pandas",
     "why": "You cannot clean what you have not measured. The file never uses blank cells for 'missing'.",
     "rule": "Count the fake missing values (-1, Unknown, N/A), the repeated rows and the odd formats. Change nothing.",
     "examples": [ex(c, f"{fmt(n)} of {fmt(n_raw)} rows", f"{n / n_raw:.1%} missing") for c, n in top_missing],
     "numbers": [num("rows", fmt(n_raw)), num("columns", str(raw.shape[1])), num("repeated rows", fmt(dup_raw))],
     "check": "Read-only step, nothing to break."},
    {"id": "missing", "step": 2, "group": "file", "title": "Real empty values", "tool": "Python + pandas",
     "why": "A fake value like -1 is still a value, so an average would use it.",
     "rule": "Replace -1, Unknown and N/A with one real empty value. Drop the Competitors column (74.6% empty).",
     "examples": [ex("Rating", raw_i.at[i_missing, "Rating"], "empty"), ex("Founded", raw_i.at[i_missing, "Founded"], "empty"),
                  ex("Revenue", "Unknown / Non-Applicable", "empty")],
     "numbers": [num("Rating made empty", fmt(missing["Rating"])), num("Founded made empty", fmt(missing["Founded"])),
                 num("Revenue made empty", fmt(missing["Revenue"])), num("column dropped", "Competitors")],
     "check": "Every real value unchanged, every placeholder now empty, same rows."},
    {"id": "company", "step": 3, "group": "data", "title": "Company name", "tool": "Python regex",
     "why": "The rating was glued onto the name after a line break, so one company looked like several.",
     "rule": "Keep the text before the line break. The Rating column is not changed, only compared.",
     "examples": [ex("Company Name", raw_i.at[i_main, "Company Name"].replace("\n", " ⏎ "), clean_i.at[i_main, "company"])],
     "numbers": [num("names fixed", fmt(glued.sum())), num("rating mismatches listed", str(glued_mismatch)),
                 num("distinct companies", f"{companies_before} before, {companies_after} after")],
     "check": "No company was split into two names, and no name became empty."},
    {"id": "salary", "step": 4, "group": "data", "title": "Salary", "tool": "Python regex",
     "why": "Text like '$137K-$171K' cannot be averaged or sorted.",
     "rule": "Read the two numbers (K means thousand) and add the middle and the source.",
     "examples": [ex("Salary Estimate", raw_i.at[i_main, "Salary Estimate"],
                     f"{fmt(clean_i.at[i_main, 'salary_min'])} to {fmt(clean_i.at[i_main, 'salary_max'])}")],
     "numbers": [num("salaries read", f"{int(st4['salary_min'].notna().sum()):,} of {len(st4):,}"), num("median salary", f"${mid.median():,.0f}"),
                 num("employer estimates", fmt((st4['salary_source'] == 'employer_est').sum()))],
     "check": "Min never above max, all between $10K and $500K."},
    {"id": "ranges", "step": 5, "group": "data", "title": "Size, revenue, founded", "tool": "Python rules",
     "why": "Ranges stored as text cannot be sorted or filtered.",
     "rule": "Read each range into min and max numbers. An open range keeps one side empty on purpose. Age = 2020 minus founded.",
     "examples": [ex("Size", raw_i.at[i_open, "Size"], f"min {fmt(clean_i.at[i_open, 'size_min'])} · max empty"),
                  ex("Revenue", raw_i.at[i_open, "Revenue"], f"min {fmt(clean_i.at[i_open, 'revenue_min'])} · max empty"),
                  ex("Founded", raw_i.at[i_main, "Founded"], f"{clean_i.at[i_main, 'founded']} · age {clean_i.at[i_main, 'company_age']}")],
     "numbers": [num("open size ranges", fmt(sizes_open)), num("open revenue ranges", fmt(revenue_open)), num("median company age", f"{age.median():.0f} years")],
     "check": "Min never above max, founded year realistic."},
    {"id": "location", "step": 6, "group": "data", "title": "Location", "tool": "Python rules",
     "why": "One text cell cannot be filtered by state or by remote.",
     "rule": "Split into city, state and a remote flag. Split the headquarters the same way, with a country.",
     "examples": [ex("Location", raw_i.at[i_main, "Location"], f"{clean_i.at[i_main, 'city']} · {clean_i.at[i_main, 'state']}"),
                  ex("Location", "Remote", "no city, no state · is_remote = True"),
                  ex("Headquarters", raw_i.at[i_foreign, "Headquarters"],
                     f"{clean_i.at[i_foreign, 'hq_city']} · {clean_i.at[i_foreign, 'hq_country']}")],
     "numbers": [num("remote jobs", fmt((st6['is_remote'] == 'True').sum())), num("HQ in the US", fmt(hq_us)), num("HQ abroad", fmt(hq_foreign))],
     "check": "Every state code is a real US state. Broken values are left empty, never guessed."},
    {"id": "title", "step": 7, "group": "data", "title": "Job title", "tool": "Python word rules",
     "why": "172 different titles are really a few kinds of job. The role and the level are two separate things.",
     "rule": "Role from the role words, level from the level words. No level word means not_stated, never a guess.",
     "examples": [ex("Job Title", t, f"{clean_i.at[i, 'title_family']} · {clean_i.at[i, 'seniority']}") for t, i in title_rows.items()],
     "numbers": [num("distinct titles", str(raw['Job Title'].nunique())), num("data_scientist", fmt(families.get("data_scientist", 0))),
                 num("other", fmt(families.get("other", 0)))],
     "check": "The medians change by 0.0% when doubtful titles are removed."},
    {"id": "duplicates", "step": 8, "group": "file", "title": "Duplicates", "tool": "Python + pandas",
     "why": "The same job appears many times, mostly with only the salary different. No date column tells us why.",
     "rule": "Remove only exact copies (saved in a separate file). Keep salary variants and flag them.",
     "examples": [ex("Same job, repeated", f"{biggest} copies in the file", f"{int(clean['company'].eq('Hatch Data Inc').sum())} kept, flagged")],
     "numbers": [num("exact copies removed", fmt(len(removed))), num("rows flagged", fmt(flagged)), num("rows left", fmt(n_clean))],
     "check": "No rows lost, no exact copies left."},
    {"id": "extract", "step": 9, "group": "data", "title": "Skills, years, degree", "tool": "Rules + Claude Haiku 5.5",
     "why": "The most useful facts are hidden in the long job description.",
     "rule": "Two methods on all rows. The AI returns JSON with an exact quote, code checks the quote, a failed check is sent back to be fixed. 30 hand labels decide who is trusted.",
     "excerpt": excerpt,
     "examples": [ex("skills (rules)", "found in the text", str(r["skills"]).replace("|", " · ")),
                  ex("Years in the text", (re.search(r"\d+\s*(?:[-–]|to)?\s*\d*\+?\s*years?", str(quote), re.I) or re.search(r".+", str(quote))).group(0).strip(), f"min {r['min_years']} years"), ex("degree (rules)", "found in the text", str(r["degree_required"]))],
     "numbers": [num("AI cost, all rows", f"${ai_cost:.2f}"), num("AI repairs needed", str(ai_repairs)), num("rows with years", fmt(years_found))],
     "check": "Years 0 to 20, and every quote must be copied word for word from the description."},
    {"id": "validate", "step": 10, "group": "file", "title": "Final check", "tool": "Python + pandas",
     "why": "Each step checked its own column. This checks that all columns still make sense together.",
     "rule": f"{n_checks} checks on every row. A failing row is listed for review, never deleted or changed.",
     "examples": [ex("Result", f"{n_checks} checks", f"{len(review)} failed")], "numbers": [num("checks", str(n_checks)), num("failures", str(len(review))),
                                 num("salaries above $300K (kept, real)", str(suspicious.get("salary max above $300K", 0)))],
     "check": "It catches impossible values. It cannot prove a value is true."},
]

# ---------- one short sentence and one main example per step (this is all the screen shows on a card) ----------
ACTIONS = {
    "profile": f"Counted what is missing. Competitors is {missing['Competitors'] / n_raw:.0%} empty.",
    "missing": "Turned fake blanks like -1 into real empty values.",
    "company": f"Removed the rating stuck to {fmt(glued.sum())} company names.",
    "salary": f"Turned {fmt(len(st4))} salary texts into numbers.",
    "ranges": "Turned size, revenue and founded year into numbers.",
    "location": "Split each place into city, state and remote.",
    "title": f"Grouped {raw['Job Title'].nunique()} titles into a role and a level.",
    "duplicates": f"Removed {len(removed)} exact copies and flagged {fmt(flagged)} repeats.",
    "extract": "Read skills, years and degree from the long text.",
    "validate": f"Ran {n_checks} checks on every row. {len(review)} failed.",
}
PRIMARY = {"extract": 1}  # which example to show when a step has several
for st in steps:
    st["action"] = ACTIONS[st["id"]]
    st["primary"] = PRIMARY.get(st["id"], 0)

# the same job before and after (the first and the last card)
c0 = clean_i.loc[i_main]
story = {
    "before": [["Job Title", raw_i.at[i_main, "Job Title"]], ["Company Name", raw_i.at[i_main, "Company Name"].replace("\n", " ⏎ ")],
               ["Salary Estimate", raw_i.at[i_main, "Salary Estimate"]], ["Location", raw_i.at[i_main, "Location"]]],
    "after": [["role", f"{c0['title_family']} · {c0['seniority']}"], ["company", c0["company"]],
              ["salary", f"{int(c0['salary_min']):,} to {int(c0['salary_max']):,}"], ["skills", str(c0["skills"]).replace("|", " · ")]],
}

# ---------- raw sample, preview rows, scores ----------
raw_cols = ["Job Title", "Salary Estimate", "Job Description", "Rating", "Company Name", "Location", "Headquarters", "Size", "Founded", "Revenue", "Competitors"]
raw_sample = [{c: cut(raw_i.at[i, c], 110) if c != "Company Name" else raw_i.at[i, c] for c in raw_cols} for i in ["0", "1", "2"]]
preview_cols = ["job_title", "title_family", "seniority", "company", "city", "state", "salary_mid", "skills", "min_years", "degree_required"]
prev = clean.sample(12, random_state=5)[["index"] + preview_cols]
preview = [{c: val(row[c]) for c in ["index"] + preview_cols} for _, row in prev.iterrows()]
for row in preview:
    row["skills"] = row["skills"].split("|") if row["skills"] else []

data = {
    "source": {"name": "Kaggle: Data Science Job Posting on Glassdoor", "file": "Uncleaned_DS_jobs.csv", "url": SOURCE_URL},
    "totals": {"rawRows": n_raw, "rawColumns": raw.shape[1], "cleanRows": n_clean, "cleanColumns": clean.shape[1],
               "exactCopiesRemoved": len(removed), "aiCostUsd": round(ai_cost, 2)},
    "raw": {"columns": raw_cols, "sample": raw_sample},
    "steps": steps,
    "story": story,
    "scores": scores,
    "preview": {"columns": ["index"] + preview_cols, "rows": preview},
    "links": {"clean": "/lab/data-cleaning/clean.csv", "uncleanSample": "/lab/data-cleaning/unclean_sample.csv",
              "descriptions": None, "source": SOURCE_URL},
}

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "lab-data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
shutil.copy(FINAL / "clean.csv", OUT / "clean.csv")
shutil.copy(FINAL / "unclean_sample.csv", OUT / "unclean_sample.csv")

print(f"wrote to {OUT}")
for f in sorted(OUT.iterdir()):
    print(f"  {f.name:<22}{f.stat().st_size / 1024:>8,.0f} KB")
print(f"steps: {len(steps)}   examples: {sum(len(s['examples']) for s in steps)}   preview rows: {len(preview)}")
