---
marp: true
theme: default
paginate: true
---

# Concept induction on the CTU Hepatitis relational database

DL-Learner class expressions for hepatitis type, compared with trees and forests

**Group 8** · Kamal Mustafayev · Elvin Mahmudzada · Huseyn Babayev
Symbolic Learning · final solution: branch `dev` · alternative: branch `enmda`

---

## 1 · Dataset and knowledge base

- **Hepatitis_std** (CTU Prague, from PKDD'02): 7 tables, 12,927 rows, 500 patients, target `dispat.Type` (294 Type 1 / 206 Type 0)
- `Bio` profiles (shared rows, 1–5 per patient) · `indis` lab records (0–105 per patient) · `inf` duration record (0–1)
- OWL KB (Owlready2): 6,419 individuals, roles `hasBioProfile`, `hasLabRecord`, `hasDurationRecord`
- Codes → value classes (`GOT_3 ⊑ LabRecord`) **and** integer data properties (`gotCode = 3`)
- `Type` never enters the KB · v2 adds 16 disjointness axioms · `noinf` drops the duration table

![height:230](../results/figures/artefacts.png)

---

## 2 · Architecture of the final solution (`dev`)

```
SQL dump → prepare_dataset → validate_data (56 checks)
         → build_ontology (v1, v2, v2_noinf) → create_split (80/20, seed 42) → eda
         → make_dl_configs (grid.json → 21 .conf) → run_dl_learner (logs → tables)
         → evaluate_concepts (own CWA evaluator + HermiT OWA)
         → propositionalise → baseline_ml → compare → report
```

- One command: `run_all.sh` / `run_all.ps1` / `make all`; Windows and Linux; Java 21/25 fix built in
- Every DL-Learner training accuracy reproduced by our evaluator: 215 / 215 concepts
- All logs, tables, figures and `.conf` files committed

---

## 3 · Learning problem and settings varied

- P = 235 Type-1, N = 165 Type-0 **training** patients; 100 test patients unseen by the learner
- CELOE / OCEL, closed-world reasoner, start class `Patient`
- Languages: **EL** (⊓ ⊔ ∃) · **ALC** (+¬ ∀) · **ALCQ** (+≥n/≤n) · **ALC(D)** (+`code ≥ k`) · FULL
- Varied: runtime 30/120/300 s · depth 4/7/12 · heuristic penalty 0.02/0.1/0.3 · **noise 0–90 %** · accuracy measure · OCEL · KB variants

---

## 4 · What was learned

| Run | Concept | Train | Test acc | Test P / R / F1 |
|---|---|---:|---:|---|
| ALC, 120 s | `∃hasDurationRecord.⊤` | 0.795 | 0.84 | 1.00 / 0.73 / 0.84 |
| EL, 120 s | `(Age_5 ⊓ Sex_1) ⊔ ∃hasDurationRecord.⊤` | 0.803 | 0.82 | 0.92 / 0.76 / 0.83 |
| ALCQ, noise 90, 300 s | `Age_6 ⊔ ∃hasDurationRecord.⊤` | 0.800 | 0.83 | 0.92 / 0.78 / 0.84 |
| ALC, noise 0 | `Patient ⊓ (Sex_0 ⊔ ¬Age_0)` | 0.593 | 0.59 | trivial |
| ALC, noise 25 | `∃hasLabRecord.(CHE_6 ⊓ ¬ZTT_1)` | 0.725 | 0.72 | 0.68 / 0.98 / 0.81 |
| ALC, **no `inf`** | `∃hasLabRecord.(ZTT_5 ⊓ ¬GPT_3)` | 0.738 | 0.67 | 0.80 / 0.59 / 0.68 |
| ALC(D), no `inf`, 300 s | `∃hasLabRecord.(ZTT_5 ⊔ (ALB_0 ⊓ TTT_0))` | 0.750 | 0.67 | 0.73 / 0.70 / 0.71 |

- Every language converges on the same perfectly precise but **spurious** role concept
- **Noise** decides what is findable: 0 % → tautologies · 25 % → lab concepts · ≥ 50 % → artefact
- Richer language = larger branching factor (EL 193k vs FULL 59k descriptions / 120 s), not better concepts

---

## 5 · Open world vs closed world

| Concept | CWA | OWA v1 (no disjointness) | OWA v2 (disjoint) |
|---|---:|---:|---:|
| `∃hasDurationRecord.⊤` | 196 | 196 | 196 |
| `Patient ⊓ (Sex_0 ⊔ ¬Age_0)` | 498 | 355 | 498 |
| `∃hasLabRecord.(ZTT_5 ⊓ ¬GPT_3)` | 254 | 0 (timeout) | 254 |
| `Age_6 ⊔ (≥2 hasLabRecord.ZTT_5)` | 249 | 71 | 243 |
| `∀hasLabRecord.¬CHE_2` | 475 | not entailed | not entailed |

- Existentials: identical · negation and cardinality: need the disjointness axioms · ∀: needs closure axioms
- Learn with the closed-world reasoner, but add the axioms before reading ¬ / ∀ concepts as facts

---

## 6 · Baseline on the same split and interpretation

| Features (107 propositionalised) | Tree (depth, leaves) | Tree F1 | Forest F1 | DL concept F1 |
|---|---|---:|---:|---:|
| sex, age only | 4, 10 | 0.66 | 0.66 | – |
| all relational | 4, 8 | 0.92 | 0.95 | 0.84 |
| without artefacts | 3, 6 | 0.84 | 0.86 | 0.71 |

- Flat table is at chance: all signal is relational; the tree's root is the same artefact (`dur_value`)
- Baselines win on accuracy through **aggregation** over one-to-many lab records (means, modes, counts)
- DL concepts win on readability (one sentence over the schema), precision 1.0, and made the artefact visible
- Short concepts generalise (train ≈ test); longer disjunctions overfit by about 1 point

---

## 7 · Conclusions of the final solution

- Relational DB → OWL KB → DL-Learner → CWA + OWA evaluation → same-split baselines, fully reproducible
- Best DL concept: test F1 0.84 (precision 1.0) but a data-collection artefact; without it 0.68–0.71 vs 0.84–0.86 for the baselines
- Lessons: the noise parameter is a hard shape constraint in CELOE · disjointness / closure axioms are prerequisites for ¬ and ∀ under OWA · concept length regularises
- Limits: undocumented code semantics · single split · ABox size at CELOE's practical limit

---

## 8 · Experimental alternative: branch `enmda`

Developed in parallel by Elvin Mahmudzada to test a different protocol

- Data pulled directly from CTU's MariaDB with `pymysql`; foreign keys read from `information_schema`
- Two ontologies: integer data properties **or** one class per bin; duration table **excluded by default**
- **5-fold stratified CV**, P = Hepatitis B (Type 0); 12 settings × 5 folds = 60 CELOE runs, 60 s, noise 30 %
- Own closed-world evaluator (reproduces a `max`-cardinality quirk of DL-Learner); HermiT check on a 20-patient sample

| Setting | Concept | Test acc | Test F1 |
|---|---|---:|---:|
| base / restricted / 10–180 s | `∃hasExam.(che ∈ [2,5])` in every fold | 0.774 ± 0.03 | 0.731 ± 0.03 |
| bins as classes | `AGE_1 ⊔ ∃hasExam.(CHE_5 ⊓ ¬TP_3)` | 0.736 | 0.678 |
| noise 10 % | near-majority concepts | 0.592 | 0.650 |
| with duration table | `∀hasTherapy.⊥ ⊓ ≤1 hasBiopsy.⊤` | 0.848 | 0.845 |
| tree d4 / forest | 38 aggregate features | 0.802 / 0.866 | 0.769 / 0.831 |

---

## 9 · Comparison and why `dev` is the final solution

| | Final solution `dev` | Alternative `enmda` |
|---|---|---|
| Protocol | one 80/20 split | 5-fold CV, mean ± std |
| Primary KB | full KB, artefact analysed and ablated | artefact-free KB; full KB as leakage demo |
| Languages / settings | 5 languages, 7 axes, 21 runs | 2 languages, 7 axes, 60 runs |
| OWA | HermiT on full ABox, disjointness ablation | 20-patient sample; CELOE-with-HermiT (infeasible) |
| Artefact-free DL result | acc 0.67–0.68, F1 0.71 | acc 0.774, F1 0.731 |
| Deliverables | docs, EDA, figures, report, slides, archive | code and results |

- Same conclusions by two routes: the artefact, the noise effect, lab-based concepts around `che` / `ztt`, forests ahead on accuracy
- `enmda`'s strengths: cross-validation, artefact-free primary problem, stable interval concept · limits: no documentation, sampled OWA, machine-specific paths
- Recommended continuation: `dev` pipeline + 5-fold protocol and artefact-free primary problem

Questions?
