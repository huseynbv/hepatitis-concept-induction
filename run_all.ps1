# whole pipeline, Windows version of run_all.sh
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }

& $py src/prepare_dataset.py
& $py src/validate_data.py
& $py src/build_ontology.py
& $py src/build_ontology.py --disjoint --no-labels --output ontology/hepatitis_v2.owl
& $py src/build_ontology.py --disjoint --exclude-inf --no-labels --output ontology/hepatitis_v2_noinf.owl
& $py src/create_split.py
& $py src/eda.py
& $py src/make_dl_configs.py
& $py src/run_dl_learner.py @args
& $py src/evaluate_concepts.py
& $py src/propositionalise.py
& $py src/baseline_ml.py
& $py src/compare.py
& $py tests/test_dl_concepts.py
Write-Host "pipeline finished"
