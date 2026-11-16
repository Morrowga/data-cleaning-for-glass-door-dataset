"""Step 3 - Take the rating out of Company Name.

Raw:  "Healthfirst\\n3.1"   (name, line break, rating)
Now:  "Healthfirst"

The Rating column is NOT changed. We only compare it with the glued number
and list the rows where they disagree.

Run from the doc-extraction-lab folder:
    python src/03_company.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "unclean" / "02_missing_fixed.csv"
OUT = ROOT / "data" / "unclean" / "03_company_fixed.csv"
REPORT = ROOT / "results" / "03_company.txt"

lines: list[str] = []


def say(text: str = "") -> None:
    print(text)
    lines.append(text)


df = pd.read_csv(SRC, dtype=str)  # empty cells stay as real empty values

# ---- split "name \n rating" ----
parts = df["Company Name"].str.split("\n", n=1, expand=True)
name = parts[0].str.strip()
glued = parts[1].str.strip() if 1 in parts.columns else pd.Series(pd.NA, index=df.index)

has_glued = glued.notna() & (glued != "")
same = has_glued & (glued == df["Rating"])
differ = has_glued & (glued != df["Rating"])

clean = df.copy()
clean["Company Name"] = name

# ---- checks ----
assert len(clean) == len(df), "row count changed"
assert clean["Company Name"].notna().all(), "a company name became empty"
assert not clean["Company Name"].str.contains("\n").any(), "a line break is still in a name"
assert clean["Rating"].equals(df["Rating"]), "Rating column was changed"

say("STEP 3 - COMPANY NAME")
say(f"rows                                  : {len(clean)}")
say(f"names with a glued rating             : {int(has_glued.sum())}")
say(f"  glued number equals Rating column   : {int(same.sum())}")
say(f"  glued number is different           : {int(differ.sum())}")
say(f"names without a glued rating          : {int((~has_glued).sum())}")
say(f"distinct company names, before -> after: {df['Company Name'].nunique()} -> {clean['Company Name'].nunique()}")

say()
say("ROWS TO REVIEW (glued number differs from Rating; Rating column is kept)")
say(f"{'index':>5}  {'company':<32}{'glued':>6}{'Rating':>8}")
for i in df.index[differ]:
    say(f"{df.at[i, 'index']:>5}  {name[i][:31]:<32}{glued[i]:>6}{str(df.at[i, 'Rating']):>8}")

say()
say("check: Rating column unchanged, no empty names, no line breaks left")

clean.to_csv(OUT, index=False)
REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
say(f"saved -> {OUT.relative_to(ROOT)}")
