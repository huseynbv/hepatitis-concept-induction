"""Scores every learned concept on train/test (closed world) and the best one per run with HermiT.
"""
from pathlib import Path
import argparse
import sys
import time

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from dl_concepts import ClosedWorldKB, metrics, parse, owa_instances  # noqa: E402

TABLES = ROOT / "results" / "tables"
ONTO = ROOT / "ontology"


def example_sets():
    train = pd.read_csv(ROOT / "configs" / "folds" / "train.csv")
    test = pd.read_csv(ROOT / "configs" / "folds" / "test.csv")
    ids = lambda df, t: {f"patient_{i}" for i in df.loc[df.target == t, "patient_id"]}
    return ids(train, 1), ids(train, 0), ids(test, 1), ids(test, 0)


def owa_subprocess(kb_path, concept, timeout):
    # child process so it can time out
    import json
    import subprocess
    cmd = [sys.executable, str(ROOT / "src" / "dl_concepts.py"), "--owa", str(kb_path), concept]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return set(), f"timeout after {timeout}s"
    if proc.returncode != 0:
        return set(), (proc.stderr.strip().splitlines() or ["error"])[-1][:200]
    line = [l for l in proc.stdout.splitlines() if l.startswith("[")]
    return (set(json.loads(line[-1])) if line else set()), ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-owa", action="store_true")
    ap.add_argument("--owa-timeout", type=int, default=300, help="seconds per HermiT call")
    ap.add_argument("--owa-kbs", nargs="*", default=["hepatitis.owl", "hepatitis_v2.owl"])
    args = ap.parse_args()

    runs = pd.read_csv(TABLES / "dl_runs.csv")
    sols = pd.read_csv(TABLES / "dl_solutions.csv")
    kb_of_run = runs.set_index("run_id")["kb"].to_dict()
    trP, trN, teP, teN = example_sets()

    kbs = {}
    rows = []
    for _, s in sols.iterrows():
        kb_name = kb_of_run[s.run_id]
        if kb_name not in kbs:
            kbs[kb_name] = ClosedWorldKB(ONTO / kb_name)
        kb = kbs[kb_name]
        try:
            node = parse(s.concept)
            ext = kb.extension(node)
        except Exception as e:  # e.g. DurationRecord on the noinf KB
            rows.append({"run_id": s.run_id, "rank": s["rank"], "concept": s.concept,
                         "error": str(e)})
            continue
        tr = metrics(ext, trP, trN)
        te = metrics(ext, teP, teN)
        rows.append({
            "run_id": s.run_id, "rank": s["rank"], "kb": kb_name, "concept": s.concept,
            "length": node.length(), "depth": node.depth(), "roles": " ".join(sorted(node.roles())),
            "dl_train_acc": s.train_acc, "dl_train_f1": s.train_f1,
            **{f"train_{k}": round(v, 4) for k, v in tr.items()},
            **{f"test_{k}": round(v, 4) for k, v in te.items()},
            "train_acc_matches_dl": abs(tr["accuracy"] - s.train_acc) < 5e-4,
        })
    ev = pd.DataFrame(rows)
    ev.to_csv(TABLES / "concept_eval.csv", index=False)
    ok = ev["train_acc_matches_dl"].fillna(False)
    print(f"{len(ev)} concepts evaluated; {int(ok.sum())} reproduce DL-Learner's training accuracy")
    if (~ok).any():
        print(ev.loc[~ok, ["run_id", "rank", "concept", "dl_train_acc", "train_accuracy", "error"]]
              .to_string() if "error" in ev else "")

    if args.skip_owa:
        return

    owa_rows = []
    best = ev[ev["rank"] == 1].dropna(subset=["length"])
    for _, b in best.iterrows():
        node = parse(b.concept)
        for kb_name in args.owa_kbs:
            if "Duration" in b.concept and "noinf" in kb_name:
                continue
            t0 = time.time()
            inst, err = owa_subprocess(ONTO / kb_name, b.concept, args.owa_timeout)
            secs = time.time() - t0
            cwa = kbs.setdefault(kb_name, ClosedWorldKB(ONTO / kb_name)).extension(node)
            patients = kbs[kb_name].classes["Patient"]
            tr, te = metrics(inst, trP, trN), metrics(inst, teP, teN)
            owa_rows.append({
                "run_id": b.run_id, "concept": b.concept, "kb": kb_name,
                "cwa_patients": len(cwa & patients), "owa_patients": len(inst & patients),
                "owa_equals_cwa": (inst & patients) == (cwa & patients),
                **{f"owa_train_{k}": round(v, 4) for k, v in tr.items() if k in ("accuracy", "f1")},
                **{f"owa_test_{k}": round(v, 4) for k, v in te.items() if k in ("accuracy", "f1")},
                "reasoner_s": round(secs, 1), "error": err,
            })
            print(f"OWA {b.run_id:16} {kb_name:22} CWA={len(cwa & patients):3} OWA={len(inst & patients):3} "
                  f"({secs:.0f}s) {err}")
            pd.DataFrame(owa_rows).to_csv(TABLES / "concept_owa.csv", index=False)


if __name__ == "__main__":
    main()
