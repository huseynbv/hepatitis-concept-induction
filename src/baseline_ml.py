"""Tree and forest baselines on the same split, three feature groups, CV-tuned on train.
"""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.tree import DecisionTreeClassifier, export_text, plot_tree

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "processed"
FOLDS = ROOT / "configs" / "folds"
TABLES = ROOT / "results" / "tables"
FIGURES = ROOT / "results" / "figures"
SEED = 42


def scores(model, X, y):
    p = model.predict(X)
    return {"accuracy": accuracy_score(y, p), "precision": precision_score(y, p, zero_division=0),
            "recall": recall_score(y, p, zero_division=0), "f1": f1_score(y, p, zero_division=0)}


def main():
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    feats = pd.read_csv(DATA / "features.csv", index_col="patient_id")
    groups = json.loads((DATA / "feature_groups.json").read_text())
    train = pd.read_csv(FOLDS / "train.csv").set_index("patient_id")
    test = pd.read_csv(FOLDS / "test.csv").set_index("patient_id")
    assert (feats.loc[train.index, "target"] == train.target).all()
    assert (feats.loc[test.index, "target"] == test.target).all()

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    candidates = {
        "majority": (DummyClassifier(strategy="most_frequent"), {}),
        "decision_tree": (DecisionTreeClassifier(random_state=SEED, class_weight=None),
                          {"max_depth": [2, 3, 4, 5, 6], "min_samples_leaf": [5, 10, 20]}),
        "random_forest": (RandomForestClassifier(random_state=SEED, n_jobs=1),
                          {"n_estimators": [300], "max_depth": [None, 6, 10],
                           "min_samples_leaf": [1, 3]}),
    }

    rows, cv_rows = [], []
    for set_name, cols in groups.items():
        Xtr, ytr = feats.loc[train.index, cols], train.target
        Xte, yte = feats.loc[test.index, cols], test.target
        for model_name, (est, grid) in candidates.items():
            if grid:
                search = GridSearchCV(est, grid, cv=cv, scoring="f1", n_jobs=1, refit=True)
                search.fit(Xtr, ytr)
                model = search.best_estimator_
                best_params = search.best_params_
                cv_f1 = search.best_score_
                for params, mean_f1 in zip(search.cv_results_["params"], search.cv_results_["mean_test_score"]):
                    cv_rows.append({"feature_set": set_name, "model": model_name,
                                    "params": json.dumps(params), "cv_f1": round(mean_f1, 4)})
            else:
                model = est.fit(Xtr, ytr)
                best_params, cv_f1 = {}, None
            tr, te = scores(model, Xtr, ytr), scores(model, Xte, yte)
            size = {}
            if model_name == "decision_tree":
                size = {"depth": int(model.get_depth()), "leaves": int(model.get_n_leaves()),
                        "n_rules": int(model.get_n_leaves())}
                (TABLES / f"tree_rules_{set_name}.txt").write_text(
                    export_text(model, feature_names=list(cols), show_weights=True))
                fig, ax = plt.subplots(figsize=(min(22, 4 + 2.2 * model.get_n_leaves()), 6))
                plot_tree(model, feature_names=list(cols), class_names=["Type 0", "Type 1"],
                          filled=False, impurity=False, proportion=False, fontsize=7, ax=ax)
                ax.set_title(f"Decision tree, {set_name} features (depth {model.get_depth()}, "
                             f"{model.get_n_leaves()} leaves)", fontsize=10, loc="left")
                fig.tight_layout()
                fig.savefig(FIGURES / f"decision_tree_{set_name}.png", dpi=160)
                plt.close(fig)
            elif model_name == "random_forest":
                size = {"n_trees": len(model.estimators_),
                        "mean_depth": round(float(np.mean([t.get_depth() for t in model.estimators_])), 1)}
                imp = pd.Series(model.feature_importances_, index=cols).sort_values(ascending=False)
                imp.round(4).to_csv(TABLES / f"rf_importance_{set_name}.csv", header=["importance"])
            rows.append({"feature_set": set_name, "model": model_name, "n_features": len(cols),
                         "best_params": json.dumps(best_params), "cv_f1": cv_f1,
                         **{f"train_{k}": round(v, 4) for k, v in tr.items()},
                         **{f"test_{k}": round(v, 4) for k, v in te.items()},
                         "model_size": json.dumps(size)})
            print(f"{set_name:12} {model_name:14} test acc={te['accuracy']:.3f} "
                  f"P={te['precision']:.3f} R={te['recall']:.3f} F1={te['f1']:.3f}  {size}")

    pd.DataFrame(rows).to_csv(TABLES / "baseline_eval.csv", index=False)
    pd.DataFrame(cv_rows).to_csv(TABLES / "baseline_cv.csv", index=False)

    imp = pd.read_csv(TABLES / "rf_importance_relational.csv", index_col=0)["importance"].head(15)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.barh(range(len(imp)), imp.values[::-1], color="#2a78d6", height=0.6, linewidth=0)
    ax.set_yticks(range(len(imp)))
    ax.set_yticklabels(imp.index[::-1], fontsize=8)
    ax.set_xlabel("impurity importance", fontsize=8, color="#898781")
    ax.set_title("Random forest, relational features: top 15 importances", fontsize=10, loc="left")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.xaxis.grid(True, color="#e1e0d9", linewidth=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(FIGURES / "baseline_importance.png", dpi=200)
    plt.close(fig)
    print("written:", TABLES / "baseline_eval.csv")


if __name__ == "__main__":
    main()
