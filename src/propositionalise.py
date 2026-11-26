"""One row per patient: counts, lab aggregates, 'any code k' flags, Bio aggregates, duration.
Also writes the feature groups (flat, relational, no_artefact).
"""
from pathlib import Path
import json

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "processed"
LABS = ["got", "gpt", "alb", "tbil", "dbil", "che", "ttt", "ztt", "tcho", "tp"]


def mode(s):
    return int(s.mode().iloc[0])


def main():
    pat = pd.read_csv(DATA / "dispat.csv")
    bio = pd.read_csv(DATA / "Bio.csv")
    ind = pd.read_csv(DATA / "indis.csv")
    inf = pd.read_csv(DATA / "inf.csv")
    r11 = pd.read_csv(DATA / "rel11.csv")
    r12 = pd.read_csv(DATA / "rel12.csv")
    r13 = pd.read_csv(DATA / "rel13.csv")

    X = pat.set_index("m_id")[["sex", "age"]].copy()
    X.index.name = "patient_id"

    # Structural counts.
    X["n_bio"] = r11.groupby("m_id").size().reindex(X.index).fillna(0).astype(int)
    X["n_lab"] = r12.groupby("m_id").size().reindex(X.index).fillna(0).astype(int)
    X["n_dur"] = r13.groupby("m_id").size().reindex(X.index).fillna(0).astype(int)

    # Lab aggregates and existence indicators.
    ll = r12.merge(ind, on="in_id")
    agg = ll.groupby("m_id")[LABS].agg(["min", "max", "mean", mode])
    agg.columns = [f"{a}_{s if isinstance(s, str) else 'mode'}" for a, s in agg.columns]
    X = X.join(agg)
    for attr in LABS:
        for code in sorted(ind[attr].unique()):
            col = f"{attr}_any_{code}"
            X[col] = ll[ll[attr] == code].groupby("m_id").size().reindex(X.index).fillna(0).gt(0).astype(int)

    # Bio aggregates and indicators.
    bl = r11.merge(bio, on="b_id")
    bagg = bl.groupby("m_id")[["fibros", "activity"]].agg(["min", "max", "mean"])
    bagg.columns = [f"{a}_{s}" for a, s in bagg.columns]
    X = X.join(bagg)
    for attr in ("fibros", "activity"):
        for code in sorted(bio[attr].unique()):
            X[f"{attr}_any_{code}"] = bl[bl[attr] == code].groupby("m_id").size().reindex(X.index).fillna(0).gt(0).astype(int)

    # Duration.
    dl = r13.merge(inf, on="a_id").set_index("m_id")["dur"]
    X["dur_value"] = dl.reindex(X.index).fillna(-1).astype(int)

    # 4 patients have no lab records at all
    X = X.fillna(-1)
    X["target"] = pat.set_index("m_id")["Type"]

    X.to_csv(DATA / "features.csv")
    artefact_cols = ["n_dur", "dur_value", "n_bio"]
    groups = {
        "flat": ["sex", "age"],
        "relational": [c for c in X.columns if c != "target"],
        "no_artefact": [c for c in X.columns if c != "target" and c not in artefact_cols],
    }
    (DATA / "feature_groups.json").write_text(json.dumps(groups, indent=2))
    print(f"features.csv: {X.shape[0]} patients x {X.shape[1] - 1} features")
    for k, v in groups.items():
        print(f"  {k:12} {len(v)} features")


if __name__ == "__main__":
    main()
