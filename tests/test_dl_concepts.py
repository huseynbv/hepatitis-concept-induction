"""The closed-world evaluator must give the same training accuracies DL-Learner
reported for these concepts (CELOE on hepatitis_v2.owl, train split):
  hasDurationRecord some DurationRecord                    79.50 % / F 78.87 %
  Patient and (not (Age_4))                                62.00 %
  (not (Age_0)) and (hasDurationRecord some DurationRecord) 79.25 %
  Patient                                                  58.75 % / F 74.02 %
"""
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dl_concepts import ClosedWorldKB, metrics, parse  # noqa: E402

_KB = None


def kb():
    global _KB
    if _KB is None:
        _KB = ClosedWorldKB(ROOT / "ontology" / "hepatitis_v2.owl")
    return _KB


def train_sets():
    train = pd.read_csv(ROOT / "configs" / "folds" / "train.csv")
    pos = {f"patient_{i}" for i in train.loc[train.target == 1, "patient_id"]}
    neg = {f"patient_{i}" for i in train.loc[train.target == 0, "patient_id"]}
    return pos, neg


def acc(expr):
    pos, neg = train_sets()
    return metrics(kb().extension(parse(expr)), pos, neg)


def test_parse_roundtrip():
    node = parse("(not (Age_0)) and (hasLabRecord only (not (CHE_2)))")
    assert node.kind == "and" and node.length() == 7
    assert node.roles() == {"hasLabRecord"}
    node = parse("hasBioProfile min 2 BioProfile")
    assert node.kind == "card" and node.n == 2
    node = parse("hasLabRecord some (zttCode some integer[>= 4])")
    assert node.children[0].facets == ((">=", 4),)


def test_matches_dl_learner_training_accuracy():
    assert abs(acc("hasDurationRecord some DurationRecord")["accuracy"] - 0.7950) < 1e-6
    assert abs(acc("hasDurationRecord some DurationRecord")["f1"] - 0.7887) < 5e-4
    assert abs(acc("Patient and (not (Age_4))")["accuracy"] - 0.62) < 1e-6
    assert abs(acc("(not (Age_0)) and (hasDurationRecord some DurationRecord)")["accuracy"] - 0.7925) < 1e-6
    assert abs(acc("Patient")["accuracy"] - 0.5875) < 1e-6
    assert abs(acc("Patient")["f1"] - 0.7402) < 5e-4


def test_closed_world_constructs():
    k = kb()
    # closed world: 'only' holds for the 4 patients without lab records
    no_labs = {i for i in k.classes["Patient"] if i not in k.roles["hasLabRecord"]}
    assert len(no_labs) == 4
    assert no_labs <= k.extension(parse("hasLabRecord only Nothing"))
    assert len(k.extension(parse("hasBioProfile min 2 BioProfile")) & k.classes["Patient"]) == 82
    assert len(k.extension(parse("not (Patient)"))) == len(k.individuals) - 500


if __name__ == "__main__":
    test_parse_roundtrip()
    test_matches_dl_learner_training_accuracy()
    test_closed_world_constructs()
    print("all dl_concepts tests passed")
