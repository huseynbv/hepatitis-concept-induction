"""Step 4/5 - Run one experiment setting over all 5 folds and evaluate on TEST data.

  python src/05_run_experiment.py <setting> [--jobs 5]

For each fold: generate conf/<setting>/fold<k>.conf, run DL-Learner (folds in parallel),
parse its log, take the TOP-ranked concept, and score it with our CWA evaluator
(correct OWL semantics) on the fold's train and test examples.
Writes results/<setting>/fold<k>.log, results/<setting>/folds.csv, and prints mean ± std.
"""
import argparse
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from kb_eval import KB, extension, length, parse, scores  # noqa: E402

SOL = re.compile(r"^\d+: (.+) \(pred\. acc\.: ([\d.]+)%, F-measure: ([\d.]+)%\)", re.M)
TERM = re.compile(r"Algorithm terminated successfully \(time: ([^,]+), (\d+) descriptions tested, (\d+) nodes")


def parse_duration(s: str) -> float:
    """'1m 0s 12ms' / '60s 0ms' / '799ms' -> seconds."""
    tot = 0.0
    for v, u in re.findall(r"(\d+)(ms|s|m|h)", s):
        tot += int(v) * {"ms": 1e-3, "s": 1, "m": 60, "h": 3600}[u]
    return tot


def run_fold(setting: str, k: int) -> dict:
    conf = ROOT / "conf" / setting / f"fold{k}.conf"
    log = ROOT / "results" / setting / f"fold{k}.log"
    t0 = time.time()
    with open(log, "w") as fh:
        subprocess.run([str(ROOT / "tools" / "dllearner.sh"), str(conf)], stdout=fh,
                       stderr=subprocess.STDOUT, cwd=ROOT / "results" / setting)
    wall = time.time() - t0
    txt = log.read_text()
    sols = SOL.findall(txt.split("solutions:")[-1]) if "solutions:" in txt else []
    term = TERM.search(txt)
    if not sols:
        raise RuntimeError(f"no solutions in {log} - check the log")
    return {"fold": k, "concept": sols[0][0], "dl_train_acc": float(sols[0][1]) / 100,
            "dl_train_f1": float(sols[0][2]) / 100,
            "search_time_s": parse_duration(term.group(1)) if term else None,
            "concepts_tested": int(term.group(2)) if term else None,
            "search_tree_nodes": int(term.group(3)) if term else None,
            "wall_time_s": round(wall, 1)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("setting")
    ap.add_argument("--jobs", type=int, default=5)
    ap.add_argument("--folds", type=int, nargs="*", default=[0, 1, 2, 3, 4])
    a = ap.parse_args()

    subprocess.run([sys.executable, str(ROOT / "src" / "04_make_conf.py"), a.setting,
                    "--folds", *map(str, a.folds)], check=True)
    (ROOT / "results" / a.setting).mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(a.jobs) as pool:
        runs = list(pool.map(lambda k: run_fold(a.setting, k), a.folds))

    kb = KB(with_therapy=True)  # superset KB: evaluates concepts from every ontology variant
    folds = json.loads((ROOT / "data" / "folds.json").read_text())
    rows = []
    for r in runs:
        node = parse(r["concept"])
        ext = extension(node, kb)
        f = folds[r["fold"]]
        tr = scores(ext, f["train_pos"], f["train_neg"])
        te = scores(ext, f["test_pos"], f["test_neg"])
        rows.append({"setting": a.setting, **r, "length": length(node),
                     **{f"train_{m}": v for m, v in tr.items()},
                     **{f"test_{m}": v for m, v in te.items()}})
    df = pd.DataFrame(rows).sort_values("fold")
    df.to_csv(ROOT / "results" / a.setting / "folds.csv", index=False)

    pd.set_option("display.width", 250, "display.max_colwidth", 120)
    print(df[["fold", "concept", "length", "train_acc", "test_acc", "test_prec", "test_rec",
              "test_f1", "concepts_tested", "search_time_s"]].round(3).to_string(index=False))
    cols = ["train_acc", "train_f1", "test_acc", "test_prec", "test_rec", "test_f1", "length",
            "search_time_s", "concepts_tested"]
    print("\nmean ± std over folds:")
    for c in cols:
        print(f"  {c:16s} {df[c].mean():9.3f} ± {df[c].std():.3f}")
