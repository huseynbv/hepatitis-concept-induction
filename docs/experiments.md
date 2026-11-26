# Learning problem and experimental design

## 1. Learning problem (Step 3)

* **Target class**: patients with `Type = 1` (the larger class, 294 of 500;
  plausibly Hepatitis C, see `docs/dataset_analysis.md` §3).
* **Examples**: the stratified 80/20 split in `configs/folds/` (seed 42).
  P = 235 training Type-1 patients, N = 165 training Type-0 patients.
  Test set: 59 Type-1 and 41 Type-0 patients, never shown to the learner.
* **Leakage check**: `Type` is not in the KB (`tests/test_dl_concepts.py` and
  `src/validate_data.py`). The KB does contain structural signals that happen to
  occur in one class only (a duration record, two or more Bio links); these are
  real data, not labels, and are analysed as "spurious/trivial solutions" and
  removed in the ablation KB `hepatitis_v2_noinf.owl`.
* **Hypothesis languages** (refinement operator `rho`, start class `Patient`):

| Name | Constructors | DL-Learner options |
|---|---|---|
| EL | ⊓, ⊔, ∃r.C | `useNegation=false useAllConstructor=false useCardinalityRestrictions=false useNumericDatatypes=false` |
| ALC | EL + ¬C, ∀r.C | `useNegation=true useAllConstructor=true` |
| ALCQ | ALC + ≥n r.C, ≤n r.C (n ≤ 5) | `useCardinalityRestrictions=true cardinalityLimit=5` |
| ALC(D) | ALC + `p some integer[≥ k]` on the `*Code` properties | `useNumericDatatypes=true` |
| FULL | ALCQ(D) | all of the above |

Disjunction is always available in `rho`; `hasValue`, boolean and string
datatypes are disabled.

## 2. Settings varied (Step 4)

Generated from `configs/experiments/grid.json` by `src/make_dl_configs.py`;
every run is a committed `.conf` file in `configs/dl-learner/`.

| Group | Runs | Setting varied | Values |
|---|---|---|---|
| language | L1–L5 | hypothesis language | EL, ALC, ALCQ, ALC(D), FULL |
| runtime | T1, L2, T2 | `maxExecutionTimeInSeconds` | 30, 120, 300 |
| depth | D1, L2, D2 | `maxDepth` | 4, 7, 12 |
| heuristic | H1, L2, H2 | `expansionPenaltyFactor` (CELOE heuristic) | 0.02, 0.1, 0.3 |
| noise | N1, N2, L2, N3 | `noisePercentage` | 0, 25, 50, 75 |
| noise | N4 | accuracy method | F-measure instead of predictive accuracy |
| ablation | A1, A2 | KB without the duration table | FULL and ALC on `hepatitis_v2_noinf.owl` |
| ablation | A3 | KB without disjointness (v1) | ALC |
| algorithm | O1 | OCEL instead of CELOE | ALC |

Defaults: CELOE, `hepatitis_v2.owl`, ALC, 120 s, depth 7, noise 50 %,
expansion penalty 0.1, predictive accuracy, start class `Patient`.

**Why noise = 50 % by default.** CELOE prunes a candidate as "too weak" when it
fails to cover more than `noisePercentage` of the positives. With the default
0 % only concepts covering *all* 235 positives survive, which for this problem
means near-tautologies (`Patient and (Sex_0 or not Age_0)`, 59 %). This was
observed in the first runs and is one of the reported findings (run N1).

## 3. Evaluation (Step 5)

`src/run_dl_learner.py` parses from each log: the top-10 solutions with their
training accuracy/F-measure, every "more accurate expression found after X ms"
event (anytime curve), the number of descriptions tested, nodes in the search
tree, search time and reasoner initialisation time.

`src/evaluate_concepts.py` re-evaluates every solution with an independent
closed-world evaluator (`src/dl_concepts.py`) on the training examples (must
reproduce DL-Learner's number, checked in `tests/`) and on the test examples:
accuracy, precision, recall, F1, concept length and depth. The best concept of
each run is also evaluated under the open-world assumption with HermiT on v1
(no disjointness) and v2 (disjointness).

## 4. Baseline (Step 6)

`src/propositionalise.py` flattens the relational data into 107 patient-level
features (counts, min/max/mean/mode per lab attribute, "exists a record with
code k" indicators that mirror `∃hasLabRecord.LAB_k`, Bio aggregates, duration).
`src/baseline_ml.py` trains majority, decision tree and random forest on the
**same 400/100 split**, choosing hyperparameters by 5-fold CV on the training
patients only, for three feature sets: flat (sex, age), relational (all), and
no-artefact (without `n_dur`, `dur_value`, `n_bio`). Tree rules are exported so
they can be compared with the DL concepts for interpretability.
