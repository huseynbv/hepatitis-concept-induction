# Concept induction on the Hepatitis relational dataset

Symbolic Learning project. We learn DL class expressions that separate **Hepatitis B** from **Hepatitis C** patients
(CTU `Hepatitis_std`) using DL-Learner. The results are compared with ML baselines and with the PW 5 algorithm.

| Folder | Contents |
|---|---|
| `report/` | `report.pdf` / `report.docx` (built by `build_report.py`), `figures/` |
| `slides/` | `slides.pdf` / `slides.pptx` (10 slides with speaker notes, built by `build_slides.py`) |
| `pw5_comparison/` | the PW 5 learner applied to this problem, with its own README and results |
| `ontology/` | `hepatitis_datatype.owl` (main), `hepatitis_classes.owl`, `hepatitis_datatype_therapy.owl` (leakage demo) |
| `conf/<setting>/fold<k>.conf` | every DL-Learner configuration that was run |
| `results/` | DL-Learner logs + per-fold metrics, `summary.csv`, `baseline/`, `owa_vs_cwa/` |
| `data/` | raw CSV tables, `labels.csv`, `folds.json` (the shared 5-fold split), `flat_features.csv` |
| `src/` | the pipeline (below) |

## Reproduce
Requirements: Python 3.12 with `owlready2 pymysql pandas scikit-learn matplotlib python-docx python-pptx`, Java 21, and
[DL-Learner 1.5.0](https://github.com/SmartDataAnalytics/DL-Learner/releases/tag/1.5.0) extracted to `tools/dllearner-1.5.0/`.
Run it through `tools/dllearner.sh`, which adds the JVM `--add-opens` flags that Java 17+ needs.

```bash
python src/01_download_data.py          # CTU MariaDB -> data/raw/*.csv
python src/02_build_ontology.py --encoding datatype            # + --encoding classes, --with-therapy
python src/03_make_folds.py             # stratified 5-fold split, P = Hep B
src/run_grid.sh                         # all DL-Learner settings (05_run_experiment.py <setting>); also: base, lang_restricted
python src/06_baseline.py               # decision trees + random forest on the same folds
python src/07_owa_check.py --per-class 25 --timeout 240        # OWA (HermiT) vs CWA re-evaluation
python pw5_comparison/pw5_learner.py    # PW 5 algorithm
python src/08_summary.py && python src/09_figures.py           # results/summary.csv + figures
```

`src/kb_eval.py` is the test-set evaluator: a parser for DL-Learner's output plus closed-world semantics.
Its `dllearner_compat=True` mode reproduces an off-by-one bug in DL-Learner 1.5.0's
`max` cardinality retrieval (see the report, Section 3).
