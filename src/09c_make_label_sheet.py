"""Step 9c (part 1) - Build the hand-labelling sheet.

30 rows: 20 where the rules and the AI disagree (years, degree or skills) and 10 where they agree.
The sheet does NOT show the rules or AI answers, so they cannot influence your labels.
The answers are saved in a separate file that is only used later for scoring.

Outputs (in data/labels/):
    label_sheet.csv          fill the last 3 columns: true_skills, true_years, true_degree
    descriptions.md          the same rows as readable text (easier to read than a CSV cell)
    _answers_hidden.csv      rules + AI answers for the same rows (do not open before labelling)
    README.md                the labelling rules

Run from the doc-extraction-lab folder:
    python src/09c_make_label_sheet.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "unclean" / "09b_ai_claude-haiku-5-5.csv"
DESC = ROOT / "data" / "unclean" / "09a_rules.csv"
OUT = ROOT / "data" / "labels"
SEED = 11
PICK = {"years": 7, "degree": 7, "skills": 6, "agree": 10}

SKILLS = [
    "Python", "SQL", "R", "Java", "Scala", "C++", "SAS", "MATLAB", "Spark", "Hadoop", "Hive", "Kafka",
    "Airflow", "Snowflake", "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Git", "TensorFlow", "PyTorch",
    "Keras", "Scikit-learn", "Pandas", "NumPy", "NLP", "Deep learning", "Machine learning", "Statistics",
    "Tableau", "Power BI", "Excel",
]


def years(x) -> str:
    return "" if pd.isna(x) else str(int(float(x)))


def skill_set(v) -> set:
    return set(v.split("|")) if isinstance(v, str) else set()


ai = pd.read_csv(SRC, dtype=str)
text = pd.read_csv(DESC, dtype=str)[["index", "Company Name", "Job Description"]]
df = ai.merge(text, on="index")

df["years_diff"] = [years(a) != years(b) for a, b in zip(df["min_years_rules"], df["min_years_ai"])]
df["degree_diff"] = df["degree_rules"] != df["degree_ai"]
df["skills_diff"] = [skill_set(a) != skill_set(b) for a, b in zip(df["skills_rules"], df["skills_ai"])]
df["agree"] = ~(df["years_diff"] | df["degree_diff"] | df["skills_diff"])

chosen: list[pd.DataFrame] = []
taken: set = set()
groups = {
    "years": df[df["years_diff"]],
    "degree": df[df["degree_diff"]],
    "skills": df[df["skills_diff"] & ~df["years_diff"] & ~df["degree_diff"]],
    "agree": df[df["agree"]],
}
for name, pool in groups.items():
    pool = pool[~pool["index"].isin(taken)]
    pick = pool.sample(min(PICK[name], len(pool)), random_state=SEED)
    taken |= set(pick["index"])
    chosen.append(pick.assign(why=name))
sheet = pd.concat(chosen).sample(frac=1, random_state=SEED).reset_index(drop=True)  # shuffle so the order gives nothing away

OUT.mkdir(parents=True, exist_ok=True)

# ---- the sheet you fill in (no answers shown) ----
blank = sheet[["index", "Job Title", "Company Name", "Job Description"]].copy()
blank["true_skills"] = ""
blank["true_years"] = ""
blank["true_degree"] = ""
blank.to_csv(OUT / "label_sheet.csv", index=False)

# ---- the hidden answers, used only for scoring ----
sheet[["index", "why", "skills_rules", "skills_ai", "min_years_rules", "min_years_ai", "years_quote",
       "degree_rules", "degree_ai", "degree_quote"]].to_csv(OUT / "_answers_hidden.csv", index=False)

# ---- readable text ----
lines = ["# Labelling sheet: read here, fill in `label_sheet.csv` by the index number", ""]
for n, r in blank.iterrows():
    lines += [f"## {n + 1}/{len(blank)}  ·  index {r['index']}  ·  {r['Job Title']}  ·  {r['Company Name']}", "", r["Job Description"].strip(), "", "---", ""]
(OUT / "descriptions.md").write_text("\n".join(lines), encoding="utf-8")

(OUT / "README.md").write_text(f"""# How to label

Open `descriptions.md` to read, and fill `label_sheet.csv` (the last three columns) using the `index` number.

**true_years**: the minimum years of professional experience the role requires overall, as a whole number.
- Several numbers ("5+ years overall, 2 years of SQL")? Use the overall one.
- "3-5 years" means 3. Years written as words count ("five years" is 5).
- Ignore years that are not a requirement (company history, "10 years of growth").
- None stated: leave it empty.

**true_degree**: the lowest degree that is REQUIRED: `bachelor`, `master`, `phd` or `not_stated`.
- "preferred", "a plus" or "or equivalent experience" instead of a degree: not required, so write `not_stated`.

**true_skills**: every skill from this list that the description asks for or clearly uses, separated by `|`
(example: `Python|SQL|Spark`). Only these {len(SKILLS)} names, spelled exactly like this:

{", ".join(SKILLS)}

Leave a cell empty if nothing applies. Do not open `_answers_hidden.csv` until you have finished: it holds the
rules and AI answers and would change what you write.
""", encoding="utf-8")

print(f"rows: {len(sheet)}")
print(sheet["why"].value_counts().to_string())
print(f"wrote {OUT.relative_to(ROOT)}/label_sheet.csv, descriptions.md, README.md, _answers_hidden.csv")
