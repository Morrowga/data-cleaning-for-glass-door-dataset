# Doc Extraction Lab

Goal: take messy documents (receipts / invoices), find the bad ones, extract the data,
clean it, and finalize it. Work here first. Only when it works, bring the unclean
data, clean data, flow and steps to the portfolio Lab page.

## Folders
- data/raw      original downloads (CORD, SROIE, ...). Never edit these.
- data/unclean  the extraction output before cleaning
- data/clean    the data after cleaning and checks
- flow          notes: the steps, decisions, failure cases (this becomes the portfolio story)
- src           scripts (Python)
- results       numbers: how many caught per layer, error rate

## Plan
1. Download a public dataset into data/raw (CORD first: small, has the correct answers).
2. Extract (prompt chain) -> data/unclean
3. Check + clean -> data/clean
4. Measure against the correct answers -> results
5. Write the flow in flow/ -> then move the story to the portfolio

## Data

The raw file `Uncleaned_DS_jobs.csv` is not included in this repo. Download it from Kaggle and put it in the project root:
https://www.kaggle.com/datasets/rashikrahmanpritom/data-science-job-posting-on-glassdoor?select=Uncleaned_DS_jobs.csv

Create a `.env` file with `ANTHROPIC_API_KEY=...` only if you want to re-run step 9b (the AI step). Cached AI answers are in `results/ai_cache.jsonl`.
