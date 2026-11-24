"""Collect all experiment results (DL-Learner settings + ML baselines) into results/summary.csv."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "results"
ORDER = ["base", "lang_restricted", "rt10", "rt60", "rt180", "enc_classes", "noise10", "noise50",
         "penalty002", "penalty001", "owa_hermit", "leak_therapy"]
WHAT = {"base": "CWA, full language, 60 s, noise 30, penalty 0.1",
        "lang_restricted": "E1 no ¬/∀/cardinality", "rt10": "E2 runtime 10 s (sequential)",
        "rt60": "E2 runtime 60 s (sequential)", "rt180": "E2 runtime 180 s (sequential)",
        "enc_classes": "E3 bins as atomic classes", "noise10": "E4 noise 10%", "noise50": "E4 noise 50%",
        "penalty002": "E5 length penalty 0.02", "penalty001": "E5 length penalty 0.01",
        "owa_hermit": "E6 OWA: OWL API + HermiT", "leak_therapy": "E7 + therapy table (LEAKAGE)"}

rows = []
for s in ORDER:
    f = R / s / "folds.csv"
    if not f.exists():
        continue
    d = pd.read_csv(f)
    row = {"method": f"DL-Learner:{s}", "description": WHAT[s],
           "distinct_concepts": d.concept.nunique(), "length_or_size": d.length.mean(),
           "search_time_s": d.search_time_s.mean(), "concepts_tested": d.concepts_tested.mean(),
           "dl_vs_true_train_acc_gap": (d.dl_train_acc - d.train_acc).abs().max()}
    for m in ["train_acc", "test_acc", "test_prec", "test_rec", "test_f1"]:
        row[m] = d[m].mean(); row[m + "_std"] = d[m].std()
    rows.append(row)

b = pd.read_csv(R / "baseline" / "folds.csv")
for m, d in b.groupby("model", sort=False):
    row = {"method": f"ML:{m}", "description": "propositionalised flat table (38 features)",
           "length_or_size": d.n_nodes.mean()}
    for c in ["train_acc", "test_acc", "test_prec", "test_rec", "test_f1"]:
        row[c] = d[c].mean(); row[c + "_std"] = d[c].std()
    rows.append(row)

out = pd.DataFrame(rows)
out.to_csv(R / "summary.csv", index=False)
pd.set_option("display.width", 250)
show = out[["method", "train_acc", "test_acc", "test_acc_std", "test_prec", "test_rec", "test_f1",
            "test_f1_std", "length_or_size", "distinct_concepts", "concepts_tested", "search_time_s",
            "dl_vs_true_train_acc_gap"]]
print(show.round(3).to_string(index=False))
