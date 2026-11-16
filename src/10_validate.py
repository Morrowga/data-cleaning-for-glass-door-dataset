"""Step 10 - Validate every row of the table.

A row that fails a check is NOT deleted and NOT changed. It is listed in results/10_review.csv
with the column, the problem and the value, so you decide what to do.
Suspicious but possible values (a very old company, a very high salary) are only counted in
the report, they are not in the review file.

Run from the doc-extraction-lab folder:
    python src/10_validate.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "unclean" / "09d_final_fields.csv"
REVIEW = ROOT / "results" / "10_review.csv"
REPORT = ROOT / "results" / "10_validate.txt"

US_STATES = set("""AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK
OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC""".split())
TITLE_FAMILIES = {"data_scientist", "data_engineer", "data_analyst", "ml_engineer", "other"}
SENIORITY = {"director", "manager", "lead", "senior", "junior", "mid", "not_stated"}
DEGREES = {"bachelor", "master", "phd", "not_stated"}
SCRAPE_YEAR = 2020

lines: list[str] = []


def say(text: str = "") -> None:
    print(text)
    lines.append(text)


df = pd.read_csv(SRC, dtype=str)
num = lambda c: pd.to_numeric(df[c], errors="coerce")
rating, smin, smax, smid = num("Rating"), num("salary_min"), num("salary_max"), num("salary_mid")
zmin, zmax, rmin, rmax = num("size_min"), num("size_max"), num("revenue_min"), num("revenue_max")
founded, age, years = num("Founded"), num("company_age"), num("min_years")

# each check: name -> (column, boolean mask of FAILING rows, short problem text)
checks = {
    "rating between 1 and 5": ("Rating", rating.notna() & ~rating.between(1, 5), "rating outside 1-5"),
    "salary min <= max": ("salary_min", smin > smax, "salary min above max"),
    "salary mid between min and max": ("salary_mid", smid.notna() & ~((smid >= smin) & (smid <= smax)), "salary mid outside min-max"),
    "salary between $10K and $500K": ("salary_min", (smin < 10_000) | (smax > 500_000), "salary outside $10K-$500K"),
    "size min <= max": ("size_min", zmin > zmax, "size min above max"),
    "revenue min <= max": ("revenue_min", rmin > rmax, "revenue min above max"),
    "founded between 1700 and 2020": ("Founded", founded.notna() & ~founded.between(1700, SCRAPE_YEAR), "founded year not realistic"),
    "company age not negative": ("company_age", age < 0, "negative company age"),
    "job state is a US state": ("state", df["state"].notna() & ~df["state"].isin(US_STATES), "state code is not a US state"),
    "headquarters state is a US state": ("hq_state", df["hq_state"].notna() & ~df["hq_state"].isin(US_STATES), "hq state code is not a US state"),
    "remote rows have no city": ("is_remote", (df["is_remote"] == "True") & df["city"].notna(), "remote job has a city"),
    "title family allowed": ("title_family", ~df["title_family"].isin(TITLE_FAMILIES), "unknown title family"),
    "seniority allowed": ("seniority", ~df["seniority"].isin(SENIORITY), "unknown seniority"),
    "years 0-20": ("min_years", years.notna() & ~years.between(0, 20), "years outside 0-20"),
    "years has a quote": ("min_years", years.notna() & df["years_evidence"].isna(), "years has no evidence quote"),
    "degree allowed": ("degree_required", ~df["degree_required"].isin(DEGREES), "unknown degree value"),
    "job title not empty": ("Job Title", df["Job Title"].isna() | (df["Job Title"].str.strip() == ""), "empty job title"),
    "company name not empty": ("Company Name", df["Company Name"].isna() | (df["Company Name"].str.strip() == ""), "empty company name"),
    "description not empty": ("Job Description", df["Job Description"].isna() | (df["Job Description"].str.strip() == ""), "empty description"),
    "index is unique": ("index", df["index"].duplicated(keep=False), "index appears twice"),
}

review = []
say("STEP 10 - VALIDATE")
say(f"rows checked: {len(df)}")
say()
say(f"{'check':<36}{'failed':>7}")
for name, (col, failing, problem) in checks.items():
    say(f"{name:<36}{int(failing.sum()):>7}")
    for i in df.index[failing.fillna(False)]:
        review.append({"index": df.at[i, "index"], "Job Title": df.at[i, "Job Title"], "column": col, "problem": problem, "value": df.at[i, col]})

review_df = pd.DataFrame(review, columns=["index", "Job Title", "column", "problem", "value"])
REVIEW.parent.mkdir(exist_ok=True)
review_df.to_csv(REVIEW, index=False)

say()
say(f"failed checks in total : {len(review_df)}  (rows affected: {review_df['index'].nunique() if len(review_df) else 0})")
if len(review_df):
    say()
    say("FIRST 10 FAILURES")
    for _, r in review_df.head(10).iterrows():
        say(f"  index {r['index']:>4}  {r['column']:<16}{r['problem']}  ({r['value']})")

say()
say("SUSPICIOUS BUT POSSIBLE (counted only, not in the review file)")
say(f"  company older than 150 years : {int((age > 150).sum())}")
say(f"  salary max above $300K       : {int((smax > 300_000).sum())}")
say(f"  salary range wider than 2x   : {int(((smax / smin) > 2).sum())}")
say(f"  0 years of experience stated : {int((years == 0).sum())}")

say()
say(f"saved -> {REVIEW.relative_to(ROOT)}")
REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
