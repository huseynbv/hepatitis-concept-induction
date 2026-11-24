"""Step 6 - Non-symbolic baseline on the SAME 5 folds.

Propositionalisation (relational -> flat table, one row per patient):
  patient : sex, age
  exams   : n_exams + min / max / mean of each of the 10 lab attributes over the patient's exams
  biopsies: n_biopsies + max / mean of fibros, activity
  (4 patients without exams get NaN exam aggregates -> filled with -1 = "no exam", plus n_exams = 0)
The therapy table is excluded, as in the main ontology (leakage).

Models: decision tree (depth 2 = comparable to a short DL concept, depth 4, unlimited)
        and random forest (500 trees). Positive class = Hepatitis B.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.tree import DecisionTreeClassifier, export_text

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def build_features() -> pd.DataFrame:
    p = pd.read_csv(RAW / "dispat.csv").set_index("m_id")[["sex", "age"]]
    ex = pd.read_csv(RAW / "rel12.csv").merge(pd.read_csv(RAW / "indis.csv"), on="in_id")
    labs = [c for c in ex.columns if c not in ("in_id", "m_id")]
    agg_e = ex.groupby("m_id")[labs].agg(["min", "max", "mean"])
    agg_e.columns = [f"{a}_{f}" for a, f in agg_e.columns]
    agg_e["n_exams"] = ex.groupby("m_id").size()
    bi = pd.read_csv(RAW / "rel11.csv").merge(pd.read_csv(RAW / "Bio.csv"), on="b_id")
    agg_b = bi.groupby("m_id")[["fibros", "activity"]].agg(["max", "mean"])
    agg_b.columns = [f"{a}_{f}" for a, f in agg_b.columns]
    agg_b["n_biopsies"] = bi.groupby("m_id").size()
    X = p.join(agg_e).join(agg_b)
    X["n_exams"] = X["n_exams"].fillna(0)
    X = X.fillna(-1)
    X.index = "patient_" + X.index.astype(str)
    return X


MODELS = {
    "tree_d2": lambda: DecisionTreeClassifier(max_depth=2, random_state=0),
    "tree_d4": lambda: DecisionTreeClassifier(max_depth=4, random_state=0),
    "tree_full": lambda: DecisionTreeClassifier(random_state=0),
    "random_forest": lambda: RandomForestClassifier(n_estimators=500, random_state=0, n_jobs=2),
}

if __name__ == "__main__":
    X = build_features()
    X.to_csv(ROOT / "data" / "flat_features.csv")
    print(f"flat table: {X.shape[0]} patients x {X.shape[1]} features")
    folds = json.loads((ROOT / "data" / "folds.json").read_text())
    rows, trees = [], {}
    for f in folds:
        tr = f["train_pos"] + f["train_neg"]; te = f["test_pos"] + f["test_neg"]
        ytr = np.r_[np.ones(len(f["train_pos"])), np.zeros(len(f["train_neg"]))]
        yte = np.r_[np.ones(len(f["test_pos"])), np.zeros(len(f["test_neg"]))]
        for name, mk in MODELS.items():
            m = mk().fit(X.loc[tr], ytr)
            pred_tr, pred = m.predict(X.loc[tr]), m.predict(X.loc[te])
            size = (m.tree_.node_count if hasattr(m, "tree_")
                    else int(sum(t.tree_.node_count for t in m.estimators_)))
            rows.append({"model": name, "fold": f["fold"], "train_acc": accuracy_score(ytr, pred_tr),
                         "test_acc": accuracy_score(yte, pred), "test_prec": precision_score(yte, pred, zero_division=0),
                         "test_rec": recall_score(yte, pred), "test_f1": f1_score(yte, pred), "n_nodes": size})
            if name in ("tree_d2", "tree_d4"):
                trees.setdefault(name, []).append(export_text(m, feature_names=list(X.columns)))
    df = pd.DataFrame(rows)
    out = ROOT / "results" / "baseline"; out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "folds.csv", index=False)
    for name, txts in trees.items():
        (out / f"{name}_trees.txt").write_text(
            "\n".join(f"===== fold {k} =====\n{t}" for k, t in enumerate(txts)))
    summ = df.groupby("model").agg(["mean", "std"]).drop(columns="fold")
    pd.set_option("display.width", 250)
    print(summ.round(3).to_string())
    if hasattr(m, "feature_importances_"):
        imp = pd.Series(m.feature_importances_, X.columns).sort_values(ascending=False)
        print("\nRF top-10 feature importances (last fold):\n", imp.head(10).round(3).to_string())
    print("\n" + trees["tree_d2"][0])
