# How to label

Open `descriptions.md` to read, and fill `label_sheet.csv` (the last three columns) using the `index` number.

**true_years**: the minimum years of professional experience the role requires overall, as a whole number.
- Several numbers ("5+ years overall, 2 years of SQL")? Use the overall one.
- "3-5 years" means 3. Years written as words count ("five years" is 5).
- Ignore years that are not a requirement (company history, "10 years of growth").
- None stated: leave it empty.

**true_degree**: the lowest degree that is REQUIRED: `bachelor`, `master`, `phd` or `not_stated`.
- "preferred", "a plus" or "or equivalent experience" instead of a degree: not required, so write `not_stated`.

**true_skills**: every skill from this list that the description asks for or clearly uses, separated by `|`
(example: `Python|SQL|Spark`). Only these 33 names, spelled exactly like this:

Python, SQL, R, Java, Scala, C++, SAS, MATLAB, Spark, Hadoop, Hive, Kafka, Airflow, Snowflake, AWS, Azure, GCP, Docker, Kubernetes, Git, TensorFlow, PyTorch, Keras, Scikit-learn, Pandas, NumPy, NLP, Deep learning, Machine learning, Statistics, Tableau, Power BI, Excel

Leave a cell empty if nothing applies. Do not open `_answers_hidden.csv` until you have finished: it holds the
rules and AI answers and would change what you write.
