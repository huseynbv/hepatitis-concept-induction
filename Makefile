PYTHON ?= python

.PHONY: all data ontology split eda configs learn evaluate baseline compare test submission clean-results

all: data ontology split eda configs learn evaluate baseline compare test

data:
	$(PYTHON) src/prepare_dataset.py
	$(PYTHON) src/validate_data.py

ontology:
	$(PYTHON) src/build_ontology.py
	$(PYTHON) src/build_ontology.py --disjoint --no-labels --output ontology/hepatitis_v2.owl
	$(PYTHON) src/build_ontology.py --disjoint --exclude-inf --no-labels --output ontology/hepatitis_v2_noinf.owl

split:
	$(PYTHON) src/create_split.py

eda:
	$(PYTHON) src/eda.py

configs:
	$(PYTHON) src/make_dl_configs.py

learn:
	$(PYTHON) src/run_dl_learner.py $(ONLY)

evaluate:
	$(PYTHON) src/evaluate_concepts.py

baseline:
	$(PYTHON) src/propositionalise.py
	$(PYTHON) src/baseline_ml.py

compare:
	$(PYTHON) src/compare.py

test:
	$(PYTHON) tests/test_dl_concepts.py

submission:
	$(PYTHON) scripts/make_submission.py

clean-results:
	rm -f results/tables/*.csv results/tables/*.txt results/figures/*.png results/logs/*.log
