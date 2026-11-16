# How the Glassdoor data was cleaned (revision notes)

Raw file: `Uncleaned_DS_jobs.csv`, 672 data-science job posts, 15 columns. It is never edited.
Every step reads the previous step's file and writes a new one, so you can open any file and see exactly what that step did.

Run order: `python src/01_profile.py`, then `02_missing.py` ... `11_finalize.py` (from the `doc-extraction-lab` folder). Step 9b needs `ANTHROPIC_API_KEY` in `.env` and costs about $0.25 for all rows.

Rule of the whole project: **code first, AI only where code cannot do it, and every step checks itself.**

| Step | Script | Reads | Writes | Rows |
|---|---|---|---|---|
| 1 Profile | `01_profile.py` | raw csv | `results/01_profile.txt` | 672 |
| 2 Missing values | `02_missing.py` | raw csv | `data/unclean/02_missing_fixed.csv` | 672 |
| 3 Company name | `03_company.py` | 02 | `03_company_fixed.csv` | 672 |
| 4 Salary | `04_salary.py` | 03 | `04_salary_fixed.csv` | 672 |
| 5 Size, revenue, founded | `05_company_numbers.py` | 04 | `05_company_numbers.csv` | 672 |
| 6 Location, headquarters | `06_location.py` | 05 | `06_location_fixed.csv` | 672 |
| 7 Job title | `07_title.py` | 06 | `07_title_grouped.csv` | 672 |
| 8 Duplicates | `08_duplicates.py` | 07 | `08_deduplicated.csv`, `08_removed_duplicates.csv` | 659 |
| 9a Rules baseline | `09a_rules.py` | 08 | `09a_rules.csv` | 659 |
| 9b AI extraction | `09b_ai.py` | 09a | `09b_ai_claude-haiku-5-5.csv`, `results/ai_cache.jsonl` | 659 |
| 9c Hand labels and score | `09c_make_label_sheet.py`, `09c_score.py` | 09b | `data/labels/*`, `results/09c_score.txt` | 30 labelled |
| 9d Final fields | `09d_final_fields.py` | 09a + 09b | `09d_final_fields.csv`, `09d_extraction_audit.csv` | 659 |
| 10 Validate | `10_validate.py` | 09d | `results/10_review.csv` (empty) | 659 |
| 11 Finalize | `11_finalize.py` | 09d | `final/*` | 659 |

---

## Step 1. Profile (look, do not touch)
**Why:** you cannot clean what you have not measured.
**Finding:** the file does not use blanks for "missing". It uses `-1`, `Unknown`, `Unknown / Non-Applicable`, `N/A`. A plain `isna()` shows almost nothing missing, which is wrong.
**Numbers:** Competitors 74.6% missing, Revenue 35.7%, Founded 17.6%, Industry and Sector 10.6%, Rating 7.4%. 179 repeated rows by title+company+location. 622 company names have a rating glued on.

## Step 2. Missing values
**Problem:** fake "missing" values look like real data (a company founded in year -1, a rating of -1 that lowers the average).
**What we did:** replaced `-1`, `Unknown`, `Unknown / Non-Applicable`, `N/A` and blanks with one **real empty value** (`NaN`). Only whole-cell matches. Dropped the `Competitors` column.
**Why empty and not 0 or "No data":** a fake number or text is still a value, so averages and counts would use it. A real empty value is skipped by the code. "No data" can be shown on the website later, only for display.
**Why drop Competitors:** 74.6% empty, and it is a list inside one cell.
**Check:** every real value unchanged, every placeholder is now empty, same row count.

## Step 3. Company name
**Problem:** `Healthfirst\n3.1` (name, line break, rating). The rating is a duplicate of the Rating column, and the same company would look like different names.
**What we did:** kept the part before the line break. The Rating column is **not changed**.
**Findings:** 619 of 622 glued ratings equal the Rating column. 3 differ (Autodesk 4.0 vs 4.2, Buckman 3.5 vs 3.6, Kollasoft 3.2 vs 5.0). We kept the Rating column and listed them. The 50 missing ratings stay empty (not 0.0, a rating of 0 would mean "worst").
**Check:** 432 distinct names before and after, so no company was split.

## Step 4. Salary
**Problem:** `$137K-$171K (Glassdoor est.)` is text, so it cannot be averaged or sorted.
**What we did:** pattern read it into `salary_min`, `salary_max`, `salary_mid` (full numbers, 137K becomes 137000) and `salary_source` (`glassdoor_est` 652, `employer_est` 20). Dropped the original text.
**Check:** all 672 read, min never above max, all between $10K and $500K.

## Step 5. Size, revenue, founded
**Problem:** ranges stored as text (`1001 to 5000 employees`, `$100 to $500 million (USD)`).
**What we did:** `size_min/size_max`, `revenue_min/revenue_max`. Open ranges keep one side **empty on purpose** (`10000+ employees` has no max, `Less than $1 million` has no min). `Founded` became a whole number (nullable `Int64`). Added `company_age = 2020 - founded` (2020 because the job texts mention 2020 most). The original Size and Revenue text is kept as a display label.
**Check:** min never above max, founded year realistic, same rows.

## Step 6. Location and headquarters
**Problem:** one text cell cannot be filtered by state.
**What we did:**
- Location into `city`, `state` (2 letters), `is_remote`, `location_level` (city, state, country, remote). `Remote` is only set when the text says Remote. A state name like `Utah` becomes `UT`. `Patuxent, Anne Arundel, MD` keeps city Patuxent and state MD.
- Headquarters into `hq_city`, `hq_state` (US only), `hq_country`. Foreign values are `City, Country`.
- Dropped the original text. Nothing is guessed: 2 broken values (`New York, 061`) stay empty.
**Bug found and fixed:** `United Kingdom` has a space, so my first check rejected it. The report listed those rows, which is how we caught it.
**Check:** every state code is a real US state.

## Step 7. Job title
**Problem:** 172 different titles, but really a few kinds of job.
**What we did:** two separate columns from word rules (original title kept):
- `title_family` = the **role** only: data_scientist, data_engineer, data_analyst, ml_engineer, other.
- `seniority` = the **level**: director, manager, lead, senior, junior, mid, not_stated.
**Decisions and why:**
- **Role and level are independent.** `Data Science Manager` is role data_scientist, level manager. (My first plan made "manager" a family, which hid the role. You corrected that.)
- **No level word means `not_stated`, not "mid"**, because mid would be a guess. Roman and number levels count (`II` mid, `III` senior, `I` junior).
- **"Scientist" alone is too loose** (lab scientists), so it needs a data word. Same for engineer titles. Lab titles ("laborator") go to `other`. `Clinical Data Analyst` is kept as a data job.
- A fixed filter can miss a real data role. It goes to `other`, and the report lists every title in `other` so we can fix the word list.
**Numbers:** data_scientist 504, data_analyst 56, data_engineer 54, ml_engineer 19, other 39 (5.8%).
**Sensitivity check:** medians change by 0.0% when titles that fit two families are removed, so the grouping is stable.

## Step 8. Duplicates
**Problem:** 328 rows belong to 149 groups sharing title+company+city+state.
**Findings:** of 178 repeated rows, 8 are identical to the first copy and **170 differ only in the salary**. There is no date column, so we cannot tell whether those are the same job scraped again or different openings. Salary gaps inside a group: under 10% in 28 groups, 10 to 30% in 45, over 30% in 68. So it is not just noise.
**What we did:** removed only the **13 exact copies** (saved in `08_removed_duplicates.csv` with the row they copied). Kept the salary variants and added flags: `repeat_group_size` (rows the job had in the raw file, Hatch Data = 12) and `possible_repeat` (True for 311 rows in 146 jobs).
**Why:** removing 178 rows on a guess could delete real openings, and keeping rows is reversible. When we compute stats we run them with all rows and with one row per job, and see if it matters.

## Step 9a. Rules baseline for the descriptions
**Problem:** skills, years and degree are hidden in long text (median 3,300 characters).
**What we did (no AI):** `skills_rules` (33 skills from a fixed list, joined with `|`), `skill_count_rules`, `min_years_rules` (first "N years" within 90 characters of the word "experience", 1 to 20), `years_unclear` (2+ different numbers), `degree_rules` (lowest degree mentioned).
**Numbers:** Python 72%, Statistics 66%, Machine learning 61%, SQL 52%, R 43%. Years found in 412 of 659. Degree: bachelor 344, master 134, phd 28, not stated 153.
**Known weak spots (where AI should help):** years written as words (36 rows), `years_unclear` (98 rows), "preferred" vs "required", "or equivalent experience" (42 rows).
**Next:** 9b Claude API on the same descriptions, 9c compare both against about 50 hand-labelled rows.

---

## Step 9b. AI extraction (prompt chain)
**Same three fields, read by Claude Haiku 5.5** (`claude-haiku-5-5`, effort low). Chain per description:
1. **Extract:** Claude returns JSON that matches a fixed schema (skills from the 33-skill list, `min_years`, `degree`, plus an exact quote for years and degree).
2. **Validate (code):** years 0 to 20, and every quote must be copied word for word from the description, so the AI cannot invent evidence.
3. **Repair:** a failed check sends the exact error back, at most 2 retries (4 rows of 659 needed one).
**Cost:** $0.25 for all 659 rows (about $0.0004 per row). A first test on 20 rows with Opus 5.5 cost $0.23, about 40 times more per row, so Haiku was chosen.
**Safety:** answers are cached row by row in `results/ai_cache.jsonl`, so a rerun never pays twice. The API key stays in `.env` and is never printed.

## Step 9c. Hand labels and score
**Why:** the rules and the AI disagree on many rows, and only a person reading the text knows who is right. You labelled 30 rows (20 where the methods disagree, 10 where they agree). The sheet did **not** show either answer, so it could not bias you.
**Scoring rules:** only the 33 listed skills are scored (77 extra skills you wrote were not scored). Degree words like `Bachelor's` count as `bachelor`.
**Result:**
| | years right | degree right | skills F1 | precision | recall |
|---|---|---|---|---|---|
| Rules | 24/30 | 24/30 | 0.80 | 0.67 | 0.99 |
| Haiku | 26/30 | 23/30 | 0.81 | 0.69 | 0.99 |
Re-weighted to all rows (the labelled rows are harder than average): years about 89% AI vs 84% rules, degree about 88% vs 89%.
**Reading it:** the AI is clearly better only for years (it reads "Four years", "ten (10) years", "at least one year"). For degree and skills the free rules score the same. Skills precision is lower for both mainly because of Statistics, which both methods list where the labeller did not. With 30 rows these are rough numbers.

## Step 9d. Final fields
Chosen from the scores: `skills` and `degree_required` from the **rules**, `min_years` from the **AI** (with the quote in `years_evidence`). Both answers stay side by side in `09d_extraction_audit.csv`, so any choice can be checked.
Note: 15 rows have `min_years = 0`. They are ranges like "0-5 years of experience" (the lower number is taken), meaning the posting accepts anyone, not that the job needs zero experience.

## Step 10. Validate
20 checks on every row (rating 1 to 5, salary min <= max and $10K to $500K, founded year, US states, allowed values, years with a quote, required fields, unique index). **0 failures.** A failing row would be listed in `results/10_review.csv`, never deleted or changed. Counted but not failed: 19 companies older than 150 years, 21 salaries above $300K, 15 rows with 0 years.
**Limit:** it catches impossible values. It cannot prove a value is true. Industry, Sector and Type of ownership are free text with no rule to test, and the correctness of the extracted fields is what step 9c measured.

## Step 11. Finalize
Files in `final/`: `clean.csv` (659 rows, 35 columns, readable snake_case names, no long text), `descriptions.csv` (index + the long text), `unclean_sample.csv` (20 raw rows for the "before"), `extraction_audit.csv`, `removed_duplicates.csv`, `change_log.md` (which step changed which column).

---

## What the whole project shows
1. Most of the work is plain code with checks after every step.
2. AI was used where code is weak (reading text), and **measured** before it was trusted: it helped for years only.
3. Doubtful data was flagged, not silently fixed or deleted (salary variants, the 3 rating mismatches, 2 broken headquarters).
4. The raw file is never edited, every step writes a new file, so any number can be traced back.

## Next
Zip the folder, add the unclean and clean results to the portfolio Lab page, and design the UI for the experiment.
