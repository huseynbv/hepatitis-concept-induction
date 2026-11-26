# hepatitis-concept-induction

Concept induction in Description Logics on the CTU **Hepatitis_std** relational
database: the database is converted into an OWL knowledge base, DL-Learner
(CELOE/OCEL) learns class expressions that describe Type-1 patients, the learned
concepts are evaluated on held-out patients under closed- and open-world
semantics, and the results are compared with decision trees and random forests
trained on the same split. Course project for *Symbolic Learning*.

## Layout

```
data/raw/Hepatitis_std.sql      mysqldump of the CTU database (7 tables, 12,927 rows)
data/processed/*.csv            one CSV per table, labels.csv, features.csv (propositionalised)
ontology/hepatitis.owl          v1 knowledge base      (src/build_ontology.py)
ontology/hepatitis_v2.owl       v2 = v1 + disjointness (main KB for experiments)
ontology/hepatitis_v2_noinf.owl v2 without the duration table (artefact ablation)
configs/folds/                  fixed stratified 80/20 split (seed 42)
configs/experiments/grid.json   experiment grid (languages, runtime, depth, heuristic, noise, ablations)
configs/dl-learner/*.conf       generated DL-Learner configurations (one per run, submitted)
src/                            pipeline scripts (see below)
tests/test_dl_concepts.py       evaluator reproduces DL-Learner's training accuracies
results/tables, results/figures all numbers and figures used in the report
results/logs/*.log              full DL-Learner console output per run
docs/                           dataset analysis, modelling choices, experimental design, environment
report/, slides/                report and presentation
```

## Pipeline

| Step | Script | Produces |
|---|---|---|
| 1 | `src/prepare_dataset.py` | CSV tables from the SQL dump, row counts checked |
| 1 | `src/validate_data.py` | integrity checks (keys, FKs, nulls, duplicates, split) |
| 2 | `src/build_ontology.py [--disjoint] [--exclude-inf] [--closure] [--train-only]` | OWL knowledge bases, `labels.csv` |
| 3 | `src/create_split.py` | `configs/folds/train.csv`, `test.csv` |
| 3 | `src/eda.py` | class-conditional tables and figures, artefact analysis |
| 4 | `src/make_dl_configs.py` | `.conf` per experiment from `grid.json` + training examples |
| 4 | `src/run_dl_learner.py [--only PREFIX]` | runs DL-Learner, parses logs → `dl_runs.csv`, `dl_solutions.csv`, `dl_anytime.csv` |
| 5 | `src/evaluate_concepts.py [--skip-owa]` | test metrics per concept (CWA) and HermiT retrieval (OWA) |
| 6 | `src/propositionalise.py`, `src/baseline_ml.py` | features, tree/forest baselines on the same split |
| 7 | `src/compare.py` | summary tables and comparison figures |
| 8 | `scripts/make_submission.py` | submission archive |

Run everything with `./run_all.sh`, `.\run_all.ps1` or `make all`.

## Setup

```
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# DL-Learner 1.5.0: unzip the GitHub release into tools/dl-learner/dllearner-1.5.0
#   https://github.com/SmartDataAnalytics/DL-Learner/releases/tag/1.5.0
# Java 11+ (tested with 21 and 25); src/run_dl_learner.py adds the --add-opens flags
# that DL-Learner 1.5.0 needs on JDK 17+.
```

See `docs/environment_setup.md` for details and `docs/experiments.md` for the
experimental design.
