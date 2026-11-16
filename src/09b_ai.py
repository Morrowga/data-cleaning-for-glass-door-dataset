"""Step 9b - AI extraction (prompt chain) of skills, years of experience and degree.

Chain per description:
    1. EXTRACT  Claude reads the description and returns JSON that matches a fixed schema.
    2. VALIDATE Code checks the JSON (years 0-20, and every quote must be copied word for word
                from the description, so the model cannot invent evidence).
    3. REPAIR   If a check fails, the exact error is sent back and Claude tries again (max 2 times).

Results are cached in results/ai_cache.jsonl, so a rerun never pays twice for the same row.
The API key is read from .env and is never printed.

Run from the doc-extraction-lab folder:
    python src/09b_ai.py            # a random sample of 20 rows (default)
    python src/09b_ai.py --n 50     # a bigger sample
    python src/09b_ai.py --all      # every row
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Literal, Optional

import anthropic
import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "unclean" / "09a_rules.csv"
CACHE = ROOT / "results" / "ai_cache.jsonl"
load_dotenv(ROOT / ".env")  # puts ANTHROPIC_API_KEY into the environment, nothing is printed

# ---------- settings you can change ----------
MODEL = "claude-haiku-5-5"  # chosen for cost. The first 20-row test used "claude-opus-5-5" (about 40x more expensive)
EFFORT = "low"  # extraction is simple, so low effort is enough
MAX_REPAIRS = 2
PRICE_PER_MILLION = {  # USD (input, output). Haiku 5.5 price is for prompts up to 100K tokens
    "claude-opus-5-5": (4.00, 20.00),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
}
SKILLS = [
    "Python", "SQL", "R", "Java", "Scala", "C++", "SAS", "MATLAB", "Spark", "Hadoop", "Hive", "Kafka",
    "Airflow", "Snowflake", "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Git", "TensorFlow", "PyTorch",
    "Keras", "Scikit-learn", "Pandas", "NumPy", "NLP", "Deep learning", "Machine learning", "Statistics",
    "Tableau", "Power BI", "Excel",
]
DEGREES = ["bachelor", "master", "phd", "not_stated"]

SYSTEM = f"""You extract facts from one data-science job description. Return only the JSON the schema asks for.

skills: every skill from this list that the description asks for or clearly uses: {", ".join(SKILLS)}.
  Use the exact spelling from the list. Do not add skills that are not in the list.
min_years: the minimum years of professional experience the role requires overall, as a whole number.
  If it names several numbers (for example "5+ years overall, 2 years of SQL"), return the overall requirement.
  Ignore years that are not a requirement (company history, "10 years of growth"). Use null if the description gives none.
  Years written as words count ("five years" is 5). For a range ("3-5 years") return the lower number.
years_quote: the exact words from the description that show min_years, copied word for word. Empty string if min_years is null.
degree: the lowest degree the description REQUIRES: bachelor, master or phd.
  A degree that is only "preferred" or "a plus" does not count. If no degree is required, return not_stated.
degree_quote: the exact words from the description that show the degree, copied word for word. Empty string if not_stated."""

SCHEMA = {
    "type": "object",
    "properties": {
        "skills": {"type": "array", "items": {"type": "string", "enum": SKILLS}},
        "min_years": {"type": ["integer", "null"]},
        "years_quote": {"type": "string"},
        "degree": {"type": "string", "enum": DEGREES},
        "degree_quote": {"type": "string"},
    },
    "required": ["skills", "min_years", "years_quote", "degree", "degree_quote"],
    "additionalProperties": False,
}


class Extraction(BaseModel):
    skills: list[str]
    min_years: Optional[int]
    years_quote: str
    degree: Literal["bachelor", "master", "phd", "not_stated"]
    degree_quote: str


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def check(result: Extraction, description: str) -> list[str]:
    """Step 2 of the chain: rules the AI answer must pass. Returns a list of problems."""
    problems = []
    text = normalize(description)
    if result.min_years is not None and not 0 <= result.min_years <= 20:
        problems.append(f"min_years {result.min_years} is outside 0-20")
    if result.min_years is not None and not result.years_quote.strip():
        problems.append("min_years is set but years_quote is empty")
    if result.min_years is None and result.years_quote.strip():
        problems.append("years_quote is set but min_years is null")
    if result.years_quote.strip() and normalize(result.years_quote) not in text:
        problems.append("years_quote is not copied word for word from the description")
    if result.degree != "not_stated" and not result.degree_quote.strip():
        problems.append("degree is set but degree_quote is empty")
    if result.degree_quote.strip() and normalize(result.degree_quote) not in text:
        problems.append("degree_quote is not copied word for word from the description")
    unknown = [s for s in result.skills if s not in SKILLS]
    if unknown:
        problems.append(f"skills not in the list: {unknown}")
    return problems


def extract_one(client: anthropic.Anthropic, description: str) -> dict:
    """Run the chain for one description. Returns the answer plus tokens, attempts and any error."""
    messages = [{"role": "user", "content": f"Job description:\n\n{description}"}]
    tokens_in = tokens_out = 0
    problems: list[str] = []
    for attempt in range(1, MAX_REPAIRS + 2):
        response = client.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=SYSTEM,
            messages=messages,
            output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": SCHEMA}},
        )
        tokens_in += response.usage.input_tokens
        tokens_out += response.usage.output_tokens
        if response.stop_reason == "refusal":
            return {"ok": False, "error": "refusal", "attempts": attempt, "tokens_in": tokens_in, "tokens_out": tokens_out}
        raw = next((b.text for b in response.content if b.type == "text"), "")
        try:
            result = Extraction.model_validate_json(raw)
            problems = check(result, description)
        except ValidationError as e:
            result, problems = None, [f"the JSON does not match the schema: {e.errors()[0]['msg']}"]
        if not problems:
            return {"ok": True, "attempts": attempt, "tokens_in": tokens_in, "tokens_out": tokens_out, **result.model_dump()}
        # Step 3 of the chain: send the exact error back and ask again
        messages += [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": "That answer failed these checks:\n- " + "\n- ".join(problems) + "\nReturn the corrected JSON."},
        ]
    return {"ok": False, "error": "; ".join(problems), "attempts": MAX_REPAIRS + 1, "tokens_in": tokens_in, "tokens_out": tokens_out}


def load_cache() -> dict:
    cache = {}
    if CACHE.exists():
        for line in CACHE.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row.get("model") == MODEL:
                cache[row["index"]] = row
    return cache


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=20, help="how many random rows (default 20)")
    parser.add_argument("--all", action="store_true", help="run every row")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. Put it in doc-extraction-lab/.env")

    df = pd.read_csv(SRC, dtype=str)
    rows = df if args.all else df.sample(args.n, random_state=7)
    client = anthropic.Anthropic()  # reads the key from the environment
    cache = load_cache()
    CACHE.parent.mkdir(exist_ok=True)

    print(f"model {MODEL}, effort {EFFORT}, rows {len(rows)} (already cached: {sum(i in cache for i in rows['index'])})")
    for n, (_, row) in enumerate(rows.iterrows(), 1):
        idx = row["index"]
        if idx in cache:
            continue
        try:
            out = extract_one(client, row["Job Description"])
        except anthropic.RateLimitError:
            out = {"ok": False, "error": "rate limit (try again later)", "attempts": 0, "tokens_in": 0, "tokens_out": 0}
        except anthropic.APIStatusError as e:
            out = {"ok": False, "error": f"API error {e.status_code}", "attempts": 0, "tokens_in": 0, "tokens_out": 0}
        except anthropic.APIConnectionError:
            out = {"ok": False, "error": "connection error", "attempts": 0, "tokens_in": 0, "tokens_out": 0}
        out.update(index=idx, model=MODEL)
        cache[idx] = out
        with CACHE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(out, ensure_ascii=False) + "\n")
        print(f"  {n:>3}/{len(rows)}  index {idx:>4}  ok={out['ok']}  attempts={out['attempts']}  tokens {out['tokens_in']}+{out['tokens_out']}")

    # ---- save a table next to the rules result ----
    price_in, price_out = PRICE_PER_MILLION.get(MODEL, (0, 0))
    table = []
    for _, row in rows.iterrows():
        r = cache[row["index"]]
        table.append({
            "index": row["index"], "Job Title": row["Job Title"],
            "skills_rules": row["skills_rules"], "skills_ai": "|".join(r.get("skills", [])) or None,
            "min_years_rules": row["min_years_rules"], "min_years_ai": r.get("min_years"),
            "years_quote": r.get("years_quote"),
            "degree_rules": row["degree_rules"], "degree_ai": r.get("degree"), "degree_quote": r.get("degree_quote"),
            "ai_ok": r["ok"], "ai_attempts": r["attempts"], "ai_error": r.get("error"),
            "tokens_in": r["tokens_in"], "tokens_out": r["tokens_out"],
            "cost_usd": round(r["tokens_in"] / 1e6 * price_in + r["tokens_out"] / 1e6 * price_out, 5),
        })
    out_table = pd.DataFrame(table)
    out_path = ROOT / "data" / "unclean" / (f"09b_ai_{MODEL}.csv" if args.all else f"09b_ai_sample_{MODEL}.csv")
    out_table.to_csv(out_path, index=False)

    ok = out_table["ai_ok"].astype(bool)
    print()
    print(f"rows done        : {len(out_table)}   passed all checks: {int(ok.sum())}   failed: {int((~ok).sum())}")
    print(f"needed a repair  : {int((out_table['ai_attempts'] > 1).sum())}")
    print(f"tokens           : {int(out_table['tokens_in'].sum()):,} in, {int(out_table['tokens_out'].sum()):,} out")
    print(f"cost             : ${out_table['cost_usd'].sum():.3f}  (about ${out_table['cost_usd'].mean():.4f} per row)")
    print(f"saved -> {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
