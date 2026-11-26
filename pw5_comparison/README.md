# Comparison with the PW 5 concept-induction algorithm

`pw5_learner.py` applies the algorithm built in Practical Work 5 (`ci_DL_skeleton.ipynb`) to the
Hepatitis learning problem, using **the same 5 folds** as DL-Learner and the ML baselines.

## What is ported from PW 5
- **Concept syntax tree**: `Top`, `Bottom`, `Atom`, `And`, `Or`, `Not`, `Exists`, `Forall` (Exercises 1 and 7).
- **Finite-interpretation semantics** `instances()`. This is closed-world, the same as DL-Learner's closed world reasoner.
- **Refinement operator** `building_blocks` + `refine_ext`. A concept is a conjunction of blocks:
  `A`, `¬A`, `A ⊔ B`, `∃r.⊤`, `∃r.A`, `∀r.A`, and fillers inside quantifiers can be refined further (Exercise 7).
- **Score** = training errors + λ · size (`node_count`) (Exercise 6.2).
- **`greedy_search(beam_width)`**: a TODO in the notebook, completed here as a scored beam search from ⊤.
  It stops when a step does not improve the best score (or after 6 steps).

The engineering changes needed for 6,223 individuals don't alter any result:
- successor and predecessor lists are indexed
- `instances()` is memoised

The semantics were cross-checked against `src/kb_eval.py` on concepts using ∃, ∀, ¬, ⊔ and ⊓.

PW 5 only knows **atomic** concepts, so it runs on the *bins as classes* encoding:
64 atoms (`Sex0/1`, `AGE_k`, `CHE_k`, `GPT_k`, …), 2 roles, 2,402 building blocks.

## Results (test set, mean ± std over 5 folds)

| setting | test acc | test F1 | size | candidates | time / fold |
|---|---|---|---|---|---|
| greedy, λ = 1 | 0.760 ± 0.035 | 0.659 ± 0.103 | 5.8 | 6.2k | ~1 s |
| beam 5, λ = 1 | 0.760 ± 0.035 | 0.659 ± 0.103 | 5.8 | 28.9k | ~6 s |
| greedy, λ = 5 | 0.744 ± 0.030 | 0.680 ± 0.048 | 2 | 3.2k | <1 s |
| beam 5, λ = 5 | 0.744 ± 0.030 | 0.680 ± 0.048 | 2 | 13.5k | ~1 s |
| *DL-Learner, bin classes* | 0.736 ± 0.040 | 0.678 ± 0.057 | 8 | 34.6k | 60 s |
| *DL-Learner, datatype (base)* | 0.774 ± 0.030 | 0.731 ± 0.034 | 5 | 19.1k | 60 s |

Typical concepts:
- λ = 1: `EXISTS hasExam.(CHE_5 AND NOT TP_3)` in 4 of 5 folds. This is the same concept DL-Learner learns on the bin-classes ontology.
- λ = 5: `EXISTS hasExam.CHE_5`.

## Take-aways
- On the **same encoding**, the PW 5 learner matches DL-Learner, at a fraction of the runtime.
  The search problem here is easy: a short concept is found within 1–2 refinement steps.
- Widening the beam from 1 to 5 changes nothing, so greedy search is not trapped in a local optimum here.
- λ moves along the accuracy / F1 / size trade-off: a larger λ gives shorter concepts, slightly lower accuracy and better recall.
- DL-Learner's advantage comes from the **hypothesis language**, not from the search. Its numeric datatype
  restrictions express `che ≤ 5` in one step. The PW 5 language would need `CHE_0 ⊔ … ⊔ CHE_5`, which isn't
  even a single building block (only pairs `A ⊔ B` are blocks).

Output: `results/folds.csv` (per fold) and `results/summary.csv`.
