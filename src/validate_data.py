"""Integrity checks on the CSVs, labels and split. Exit 1 on failure.
"""
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "processed"
FOLDS = ROOT / "configs" / "folds"

EXPECTED = {
    "Bio": (32, ["fibros", "activity", "b_id"]),
    "dispat": (500, ["m_id", "sex", "age", "Type"]),
    "indis": (5691, ["got", "gpt", "alb", "tbil", "dbil", "che", "ttt",
                     "ztt", "tcho", "tp", "in_id"]),
    "inf": (196, ["dur", "a_id"]),
    "rel11": (621, ["b_id", "m_id"]),
    "rel12": (5691, ["in_id", "m_id"]),
    "rel13": (196, ["a_id", "m_id"]),
}
PRIMARY_KEYS = {"Bio": "b_id", "dispat": "m_id", "indis": "in_id", "inf": "a_id"}
LINKS = {
    "rel11": ("Bio", "b_id", "dispat", "m_id"),
    "rel12": ("indis", "in_id", "dispat", "m_id"),
    "rel13": ("inf", "a_id", "dispat", "m_id"),
}


class Checker:
    def __init__(self):
        self.failures = 0

    def check(self, condition, message):
        status = "OK  " if condition else "FAIL"
        if not condition:
            self.failures += 1
        print(f"[{status}] {message}")


def main():
    c = Checker()
    tables = {}
    for name, (rows, cols) in EXPECTED.items():
        df = pd.read_csv(DATA / f"{name}.csv")
        tables[name] = df
        c.check(len(df) == rows, f"{name}: {len(df)} rows (expected {rows})")
        c.check(list(df.columns) == cols, f"{name}: columns {list(df.columns)}")
        c.check(not df.isnull().any().any(), f"{name}: no missing values")
        c.check(not df.duplicated().any(), f"{name}: no duplicate rows")

    total_rows = sum(len(df) for df in tables.values())
    total_cols = sum(df.shape[1] for df in tables.values())
    c.check(total_rows == 12927, f"total rows {total_rows} (CTU: 12,927)")
    c.check(total_cols == 26, f"total columns {total_cols} (CTU: 26)")

    for name, key in PRIMARY_KEYS.items():
        c.check(tables[name][key].is_unique, f"{name}.{key} is unique")

    for link, (lt, lk, rt, rk) in LINKS.items():
        df = tables[link]
        c.check(df[lk].isin(tables[lt][lk]).all(), f"{link}.{lk} -> {lt}.{lk} resolves")
        c.check(df[rk].isin(tables[rt][rk]).all(), f"{link}.{rk} -> {rt}.{rk} resolves")
        c.check(not df.duplicated().any(), f"{link}: no duplicate links")
        orphans = (~tables[lt][lk].isin(df[lk])).sum()
        c.check(orphans == 0, f"{lt}: {orphans} orphan records without a patient link")

    nbio = tables["rel11"].groupby("m_id").size()
    nlab = tables["rel12"].groupby("m_id").size()
    ndur = tables["rel13"].groupby("m_id").size()
    c.check(nbio.min() >= 1 and len(nbio) == 500, "every patient has >= 1 Bio link")
    c.check(len(nlab) == 496, f"{len(nlab)} patients have lab records (expected 496)")
    c.check(len(ndur) == 196 and ndur.max() == 1, "196 patients have exactly one duration record")

    # Target and labels.
    dispat = tables["dispat"]
    dist = dispat["Type"].value_counts().to_dict()
    c.check(dist == {1: 294, 0: 206}, f"target distribution {dist} (expected 0:206, 1:294)")
    labels = pd.read_csv(DATA / "labels.csv")
    c.check(list(labels.columns) == ["patient_id", "target"], "labels.csv columns")
    merged = dispat.merge(labels, left_on="m_id", right_on="patient_id")
    c.check(len(merged) == 500 and (merged["Type"] == merged["target"]).all(),
            "labels.csv agrees with dispat.Type")

    # Split.
    train = pd.read_csv(FOLDS / "train.csv")
    test = pd.read_csv(FOLDS / "test.csv")
    c.check(len(train) == 400 and len(test) == 100, f"split sizes {len(train)}/{len(test)}")
    c.check(set(train.patient_id).isdisjoint(test.patient_id), "train/test disjoint")
    c.check(set(train.patient_id) | set(test.patient_id) == set(labels.patient_id),
            "split covers all patients")
    lab = labels.set_index("patient_id")["target"]
    c.check((train.set_index("patient_id")["target"] == lab.loc[train.patient_id]).all()
            and (test.set_index("patient_id")["target"] == lab.loc[test.patient_id]).all(),
            "split labels agree with labels.csv")

    print(f"\n{c.failures} failure(s).")
    return 1 if c.failures else 0


if __name__ == "__main__":
    sys.exit(main())
