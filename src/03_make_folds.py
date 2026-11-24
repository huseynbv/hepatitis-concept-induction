"""Step 3 - Learning problem: P = Hepatitis B patients, N = Hepatitis C patients.

Creates ONE fixed stratified 5-fold split (seed 42) shared by DL-Learner AND the ML
baseline, so both are compared on exactly the same train/test examples.
Stratified = every fold keeps the global 206 B / 294 C ratio (~41/59).
"""
import json
from pathlib import Path

import pandas as pd
from sklearn.model_selection import StratifiedKFold

ROOT = Path(__file__).resolve().parent.parent
lab = pd.read_csv(ROOT / "data" / "labels.csv")
y = (lab.type == "B").astype(int)  # 1 = positive (Hep B)

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
folds = []
for k, (tr, te) in enumerate(skf.split(lab, y)):
    f = {"fold": k}
    for part, idx in [("train", tr), ("test", te)]:
        sub = lab.iloc[idx]
        f[f"{part}_pos"] = sorted(sub[sub.type == "B"].individual)
        f[f"{part}_neg"] = sorted(sub[sub.type == "C"].individual)
    folds.append(f)
    print(f"fold {k}: train {len(f['train_pos'])}+/{len(f['train_neg'])}-  "
          f"test {len(f['test_pos'])}+/{len(f['test_neg'])}-")

(ROOT / "data" / "folds.json").write_text(json.dumps(folds, indent=1))
print("saved data/folds.json")
