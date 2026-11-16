"""Step 9c (part 2) - Score the rules and the AI (Haiku) against your hand labels.

Reads only files that already exist. It makes no AI call and costs nothing.

    data/labels/label_sheet.csv       your labels (true_skills, true_years, true_degree)
    data/labels/_answers_hidden.csv   the rules and AI answers for the same 30 rows
    data/unclean/09b_ai_claude-haiku-5-5.csv   all 659 rows (to weight the sample fairly)

Run from the doc-extraction-lab folder:
    python src/09c_score.py
"""
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LABELS = ROOT / "data" / "labels" / "label_sheet.csv"
ANSWERS = ROOT / "data" / "labels" / "_answers_hidden.csv"
FULL = ROOT / "data" / "unclean" / "09b_ai_claude-haiku-5-5.csv"
REPORT = ROOT / "results" / "09c_score.txt"
SCORES_JSON = ROOT / "results" / "09c_score.json"  # the same numbers for the portfolio screen

SKILLS = [
    "Python", "SQL", "R", "Java", "Scala", "C++", "SAS", "MATLAB", "Spark", "Hadoop", "Hive", "Kafka",
    "Airflow", "Snowflake", "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Git", "TensorFlow", "PyTorch",
    "Keras", "Scikit-learn", "Pandas", "NumPy", "NLP", "Deep learning", "Machine learning", "Statistics",
    "Tableau", "Power BI", "Excel",
]
BY_LOWER = {s.lower(): s for s in SKILLS}
ALIASES = {"c/c++": "C++"}  # the only label spelling that clearly means a listed skill
DEGREE_WORDS = {"bachelor's": "bachelor", "bachelors": "bachelor", "master's": "master", "masters": "master", "phd": "phd"}

lines: list[str] = []


def say(text: str = "") -> None:
    print(text)
    lines.append(text)


# ---------- normalise one value the same way for labels and answers ----------
def years(x) -> str:
    return "" if pd.isna(x) or str(x).strip() == "" else str(int(float(x)))


def degree(x) -> str:
    s = "" if pd.isna(x) else str(x).strip().lower()
    return DEGREE_WORDS.get(s, s) or "not_stated"


def skills(x) -> set:
    if pd.isna(x) or not str(x).strip():
        return set()
    out = set()
    for part in str(x).split("|"):
        key = part.strip().lower()
        key = ALIASES.get(key, key)
        key = BY_LOWER.get(key.lower(), None) if key.lower() in BY_LOWER else (key if key in SKILLS else None)
        if key:
            out.add(key)
    return out


lab = pd.read_csv(LABELS, dtype=str, keep_default_na=False).set_index("index")
ans = pd.read_csv(ANSWERS, dtype=str).set_index("index")
rows = lab.index
n = len(rows)

# only the 33 listed skills are scored. Count what is left out so nothing is hidden.
extra = sum(len([p for p in v.split("|") if p.strip()]) - len(skills(v)) for v in lab["true_skills"])

# ---------- scores ----------
methods = {"rules": ("skills_rules", "min_years_rules", "degree_rules"), "Haiku": ("skills_ai", "min_years_ai", "degree_ai")}
result = {}
for name, (sk_col, yr_col, dg_col) in methods.items():
    y_ok = {i: years(ans.at[i, yr_col]) == years(lab.at[i, "true_years"]) for i in rows}
    d_ok = {i: degree(ans.at[i, dg_col]) == degree(lab.at[i, "true_degree"]) for i in rows}
    tp = fp = fn = exact = 0
    for i in rows:
        truth, got = skills(lab.at[i, "true_skills"]), skills(ans.at[i, sk_col])
        tp += len(truth & got)
        fp += len(got - truth)
        fn += len(truth - got)
        exact += truth == got
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    result[name] = dict(y_ok=y_ok, d_ok=d_ok, tp=tp, fp=fp, fn=fn, exact=exact, precision=precision, recall=recall,
                        f1=2 * precision * recall / (precision + recall) if precision + recall else 0)

scores_json = {
    "labelled_rows": n,
    "methods": {
        name: {"years_right": int(sum(r["y_ok"].values())), "degree_right": int(sum(r["d_ok"].values())),
               "skills_f1": round(r["f1"], 3), "skills_precision": round(r["precision"], 3), "skills_recall": round(r["recall"], 3)}
        for name, r in result.items()
    },
    "estimate_all_rows": {},
}
say("STEP 9c - SCORE AGAINST YOUR HAND LABELS")
say(f"rows labelled: {n}   (20 chosen where rules and AI disagree, 10 where they agree)")
say(f"labelled skills outside the 33-skill list (not scored): {extra}")
say()
say(f"{'':<8}{'years right':>13}{'degree right':>14}{'skills F1':>11}{'precision':>11}{'recall':>8}{'rows exact':>12}")
for name, r in result.items():
    say(f"{name:<8}{sum(r['y_ok'].values()):>8}/{n}{sum(r['d_ok'].values()):>10}/{n}{r['f1']:>11.2f}{r['precision']:>11.2f}{r['recall']:>8.2f}{r['exact']:>9}/{n}")
say("  precision = of the skills it named, how many were right.  recall = of the true skills, how many it found.")

# ---------- fair estimate for all 659 rows (the sample is full of hard rows) ----------
full = pd.read_csv(FULL, dtype=str)
pop_diff = {
    "years": float(sum(years(a) != years(b) for a, b in zip(full["min_years_rules"], full["min_years_ai"])) / len(full)),
    "degree": float((full["degree_rules"] != full["degree_ai"]).mean()),
}
say()
say("ESTIMATE FOR ALL 659 ROWS (sample re-weighted: the labelled rows are harder than average)")
say(f"  share of rows where rules and AI disagree: years {pop_diff['years']:.0%}, degree {pop_diff['degree']:.0%}")
for field, col_r, col_a, true_col, norm in [
    ("years", "min_years_rules", "min_years_ai", "true_years", years),
    ("degree", "degree_rules", "degree_ai", "true_degree", degree),
]:
    differ = [i for i in rows if norm(ans.at[i, col_r]) != norm(ans.at[i, col_a])]
    same = [i for i in rows if i not in differ]
    est = {}
    for name, col in (("rules", col_r), ("Haiku", col_a)):
        acc1 = sum(norm(ans.at[i, col]) == norm(lab.at[i, true_col]) for i in differ) / len(differ) if differ else 0
        acc0 = sum(norm(ans.at[i, col]) == norm(lab.at[i, true_col]) for i in same) / len(same) if same else 0
        est[name] = pop_diff[field] * acc1 + (1 - pop_diff[field]) * acc0
    scores_json["estimate_all_rows"][field] = {"rules": round(est["rules"], 3), "haiku": round(est["Haiku"], 3)}
    say(f"  {field:<7} where they disagree (n={len(differ)}): rules {sum(norm(ans.at[i, col_r]) == norm(lab.at[i, true_col]) for i in differ)} right, "
        f"Haiku {sum(norm(ans.at[i, col_a]) == norm(lab.at[i, true_col]) for i in differ)} right   ->  estimated accuracy rules {est['rules']:.0%}, Haiku {est['Haiku']:.0%}")
say("  (small sample: treat these as rough numbers, not exact)")

# ---------- where each one is wrong ----------
for field, col_r, col_a, true_col, norm, quote in [
    ("YEARS", "min_years_rules", "min_years_ai", "true_years", years, "years_quote"),
    ("DEGREE", "degree_rules", "degree_ai", "true_degree", degree, "degree_quote"),
]:
    say()
    say(f"{field}: rows where at least one method is wrong")
    say(f"  {'index':>5}  {'you':>10}{'rules':>12}{'Haiku':>12}   Haiku quote")
    for i in rows:
        t, r_, a_ = norm(lab.at[i, true_col]), norm(ans.at[i, col_r]), norm(ans.at[i, col_a])
        if r_ != t or a_ != t:
            q = "" if pd.isna(ans.at[i, quote]) else str(ans.at[i, quote])[:60].replace("\n", " ")
            say(f"  {i:>5}  {t or '-':>10}{r_ or '-':>12}{a_ or '-':>12}   {q}")

say()
say("SKILLS: most common mistakes")
for name, (sk_col, _, _) in methods.items():
    missed, extra_ = Counter(), Counter()
    for i in rows:
        truth, got = skills(lab.at[i, "true_skills"]), skills(ans.at[i, sk_col])
        missed.update(truth - got)
        extra_.update(got - truth)
    say(f"  {name:<6} missed (you listed, it did not): {dict(missed.most_common(6))}")
    say(f"  {'':<6} extra  (it listed, you did not)   : {dict(extra_.most_common(6))}")

REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
import json
SCORES_JSON.write_text(json.dumps(scores_json, indent=2), encoding="utf-8")
print(f"\nsaved -> {REPORT.relative_to(ROOT)}")
