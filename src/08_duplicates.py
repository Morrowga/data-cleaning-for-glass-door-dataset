"""Step 8 - Remove exact copies and flag possible repeats.

1. Exact copy = identical in every column except `index`. We keep the first one and
   move the others to a separate file with the reason, so nothing is lost silently.
2. Possible repeat = same title, company, city, state and description, but a different salary.
   These stay in the data. We only add flags:
     repeat_group_size : how many rows this job had in the raw file (before removing copies)
     possible_repeat   : True if the job still has 2+ rows with different salaries

Run from the doc-extraction-lab folder:
    python src/08_duplicates.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "unclean" / "07_title_grouped.csv"
OUT = ROOT / "data" / "unclean" / "08_deduplicated.csv"
REMOVED = ROOT / "data" / "unclean" / "08_removed_duplicates.csv"
REPORT = ROOT / "results" / "08_duplicates.txt"

JOB_KEY = ["Job Title", "Company Name", "city", "state", "Job Description"]

lines: list[str] = []


def say(text: str = "") -> None:
    print(text)
    lines.append(text)


df = pd.read_csv(SRC, dtype=str)
all_columns = [c for c in df.columns if c != "index"]

# ---- how many rows each job had in the raw file ----
df["repeat_group_size"] = df.groupby(JOB_KEY, dropna=False)["index"].transform("size").astype(int)

# ---- 1. exact copies ----
is_copy = df.duplicated(subset=all_columns, keep="first")
first_index = df[~is_copy].set_index(all_columns)["index"]  # which row we kept
removed = df[is_copy].copy()
removed["kept_index"] = [first_index.loc[tuple(r[c] for c in all_columns)] for _, r in removed.iterrows()]
removed["reason"] = "exact copy of another row"
kept = df[~is_copy].copy()

# ---- 2. possible repeats among the kept rows ----
left = kept.groupby(JOB_KEY, dropna=False)["index"].transform("size")
kept["possible_repeat"] = left > 1

# ---- checks ----
assert len(kept) + len(removed) == len(df), "rows were lost"
assert not kept.duplicated(subset=all_columns).any(), "exact copies are still there"
assert (kept["repeat_group_size"] >= left).all()

say("STEP 8 - DUPLICATES")
say(f"rows before : {len(df)}")
say(f"exact copies removed : {len(removed)}")
say(f"rows after  : {len(kept)}")
say()
say("possible repeats (same job, different salary) among the kept rows")
say(f"  rows flagged possible_repeat : {int(kept['possible_repeat'].sum())}")
groups = kept[kept["possible_repeat"]].groupby(JOB_KEY, dropna=False).ngroups
say(f"  jobs with 2+ salary versions : {groups}")
say(f"  rows in jobs seen once       : {int((kept['repeat_group_size'] == 1).sum())}")
say()
say("biggest jobs by raw copies")
top = kept.sort_values("repeat_group_size", ascending=False).drop_duplicates(subset=["Company Name", "Job Title"]).head(6)
for _, r in top.iterrows():
    say(f"  {int(r['repeat_group_size']):>3} copies  {r['Company Name'][:28]:<28}{r['Job Title'][:40]}")
say()
say("removed rows (first 5)")
for _, r in removed.head(5).iterrows():
    say(f"  index {r['index']:>4} = copy of {r['kept_index']:>4}   {r['Company Name'][:28]} | {r['Job Title'][:40]}")
say()
say("check: no rows lost, no exact copies left, group sizes fit")

kept.to_csv(OUT, index=False)
removed.to_csv(REMOVED, index=False)
REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
say(f"saved -> {OUT.relative_to(ROOT)}")
say(f"saved -> {REMOVED.relative_to(ROOT)}")
