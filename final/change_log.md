# Change log

Raw file: `Uncleaned_DS_jobs.csv`, 672 rows, 15 columns.
Final file: `final/clean.csv`, 659 rows, 35 columns (+ `descriptions.csv`).

| raw column | final column(s) | step | what happened |
|---|---|---|---|
| index | index | - | kept as the row number |
| Job Title | job_title, title_family, seniority | 7 | title kept; role and level added from word rules |
| Salary Estimate | salary_min, salary_max, salary_mid, salary_source | 4 | text turned into numbers; original text dropped |
| Job Description | descriptions.csv; skills, skill_count, min_years, years_evidence, degree_required | 9 | long text moved to its own file; three facts extracted from it |
| Rating | rating | 3 | kept; -1 became empty (step 2); not changed in step 3 |
| Company Name | company | 3 | glued rating removed |
| Location | city, state, is_remote, location_level | 6 | split; original text dropped |
| Headquarters | hq_city, hq_state, hq_country | 6 | split; original text dropped |
| Size | size_label, size_min, size_max | 5 | range read into numbers; label kept |
| Founded | founded, company_age | 5 | whole number; age = 2020 - founded |
| Type of ownership | ownership | 2 | -1 / Unknown became empty |
| Industry | industry | 2 | -1 became empty |
| Sector | sector | 2 | -1 became empty |
| Revenue | revenue_label, revenue_min, revenue_max | 5 | range read into numbers (USD); label kept |
| Competitors | (dropped) | 2 | 74.6% empty and a list inside one cell |
| (new) | repeat_group_size, possible_repeat | 8 | flags for jobs seen more than once with different salaries |

## Rows

- 672 raw rows
- 13 exact copies removed in step 8 (`removed_duplicates.csv`) -> 659 rows
- Salary variants of the same job were kept and flagged (`possible_repeat`).

## Rule of the project

Code first, AI only where code cannot do it, and every step checks itself. The raw file is never edited.
