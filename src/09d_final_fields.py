"""Step 9d - Put the final skills, years and degree into the table.

Chosen from the scores in step 9c (30 hand labels):
    skills           from the RULES   (same score as the AI, free)
    min_years        from the AI      (Haiku, a bit better on years written as words)
    degree_required  from the RULES   (same score as the AI, free)

The rules answers and the AI answers are saved side by side in one audit file, so every
choice can be checked later. The final table keeps only the chosen columns.

Run from the doc-extraction-lab folder:
    python src/09d_final_fields.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "unclean" / "09a_rules.csv"  # all cleaned columns + the rules answers
AI = ROOT / "data" / "unclean" / "09b_ai_claude-haiku-5-5.csv"  # all 659 rows, Haiku answers
OUT = ROOT / "data" / "unclean" / "09d_final_fields.csv"
AUDIT = ROOT / "data" / "unclean" / "09d_extraction_audit.csv"
REPORT = ROOT / "results" / "09d_final_fields.txt"

lines: list[str] = []


def say(text: str = "") -> None:
    print(text)
    lines.append(text)


df = pd.read_csv(TABLE, dtype=str)
ai = pd.read_csv(AI, dtype=str)[["index", "min_years_ai", "years_quote", "degree_ai", "skills_ai", "ai_ok"]]
merged = df.merge(ai, on="index", how="left", validate="one_to_one")

assert len(merged) == len(df), "rows changed in the merge"
assert merged["ai_ok"].notna().all(), "a row has no AI answer"

# ---- audit file: both answers next to each other ----
merged[["index", "Job Title", "skills_rules", "skills_ai", "min_years_rules", "min_years_ai", "years_quote",
        "degree_rules", "degree_ai"]].to_csv(AUDIT, index=False)

# ---- final table ----
final = df.drop(columns=["skills_rules", "skill_count_rules", "min_years_rules", "years_unclear", "degree_rules"]).copy()
final["skills"] = merged["skills_rules"]
final["skill_count"] = merged["skill_count_rules"].astype(int)
final["min_years"] = pd.to_numeric(merged["min_years_ai"]).astype("Int64")
final["years_evidence"] = merged["years_quote"].where(merged["min_years_ai"].notna())
final["degree_required"] = merged["degree_rules"]

# ---- checks ----
assert final["degree_required"].isin(["bachelor", "master", "phd", "not_stated"]).all()
assert final["min_years"].dropna().between(0, 20).all()
assert (final["skill_count"] == final["skills"].fillna("").map(lambda s: len([x for x in s.split("|") if x]))).all()

say("STEP 9d - FINAL FIELDS")
say(f"rows    : {len(final)}")
say(f"columns : {df.shape[1]} -> {final.shape[1]}  (rules and AI columns replaced by 5 chosen ones)")
say()
say("where each final column comes from")
say("  skills, skill_count : rules")
say("  min_years           : AI (Haiku), with the exact quote in years_evidence")
say("  degree_required     : rules")
say()
say(f"skills found        : {int(final['skills'].notna().sum())} rows have at least one (median {int(final['skill_count'].median())} skills)")
say(f"min_years found     : {int(final['min_years'].notna().sum())} rows, empty in {int(final['min_years'].isna().sum())}")
say("degree_required     :")
say(final["degree_required"].value_counts().to_string())
say()
say("where the two methods gave a different years answer (kept: AI)")
differ = merged[(merged["min_years_rules"].fillna("") != merged["min_years_ai"].fillna("").str.replace(".0", "", regex=False))]
say(f"  {len(differ)} of {len(final)} rows. Both answers are in 09d_extraction_audit.csv")
say()
say("check: row count same, degree values valid, years 0-20, skill_count matches skills")

final.to_csv(OUT, index=False)
REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
say(f"saved -> {OUT.relative_to(ROOT)}")
say(f"saved -> {AUDIT.relative_to(ROOT)}")
