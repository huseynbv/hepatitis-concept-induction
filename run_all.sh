#!/usr/bin/env sh
# whole pipeline from the SQL dump to the comparison tables
# needs the venv, java and DL-Learner in tools/dl-learner/dllearner-1.5.0 (or $DLLEARNER_HOME)
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-python}

$PY src/prepare_dataset.py
$PY src/validate_data.py
$PY src/build_ontology.py                                   # v1: ontology/hepatitis.owl + labels.csv
$PY src/build_ontology.py --disjoint --no-labels --output ontology/hepatitis_v2.owl
$PY src/build_ontology.py --disjoint --exclude-inf --no-labels --output ontology/hepatitis_v2_noinf.owl
$PY src/create_split.py
$PY src/eda.py
$PY src/make_dl_configs.py
$PY src/run_dl_learner.py "$@"                              # pass --only <prefix> to run a subset
$PY src/evaluate_concepts.py
$PY src/propositionalise.py
$PY src/baseline_ml.py
$PY src/compare.py
$PY tests/test_dl_concepts.py
echo "pipeline finished"
