"""Runs DL-Learner for each .conf in configs/dl-learner and parses the logs into
results/tables (dl_runs, dl_solutions, dl_anytime). The JVM flags are needed
because DL-Learner 1.5.0 was built for Java 8.

  python src/run_dl_learner.py              all confs
  python src/run_dl_learner.py --only L1_   subset by prefix
  python src/run_dl_learner.py --parse-only re-parse existing logs
"""
from pathlib import Path
import argparse
import os
import re
import subprocess
import sys
import time

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CONF_DIR = ROOT / "configs" / "dl-learner"
LOG_DIR = ROOT / "results" / "logs"
TABLES = ROOT / "results" / "tables"

ADD_OPENS = [
    "--add-opens", "java.base/java.lang=ALL-UNNAMED",
    "--add-opens", "java.base/java.lang.invoke=ALL-UNNAMED",
    "--add-opens", "java.base/java.lang.reflect=ALL-UNNAMED",
    "--add-opens", "java.base/java.util=ALL-UNNAMED",
    "--add-opens", "java.base/java.io=ALL-UNNAMED",
    "--add-opens", "java.base/java.net=ALL-UNNAMED",
]

RE_CELOE_SOL = re.compile(r"^(\d+): (.*) \(pred\. acc\.: ([\d.]+)%, F-measure: ([\d.]+)%\)\s*$")
RE_OCEL_SOL = re.compile(r"^(\d+): (.*) \(accuracy ([\d.]+)%, length (\d+), depth (\d+)\)\s*$")
RE_IMPROVE = re.compile(r"more accurate \(([\d.]+)%\) class expression found(?: after (.+?))?: (.*)$")
RE_TERMINATED = re.compile(
    r"Algorithm terminated successfully \(time: (.+?), (\d+) descriptions tested, (\d+) nodes in the search tree\)")
RE_OCEL_STOP = re.compile(r"Algorithm stopped \((\d+) descriptions tested")
RE_REASONER = re.compile(r"initialized component 'reasoner' in (.+?)\. Status")
RE_TIME = re.compile(r"(?:(\d+)h)?\s*(?:(\d+)m)?\s*(?:(\d+)s)?\s*(?:(\d+)ms)?")


def parse_duration(text):
    # '1m 12s 345ms' -> 72.345
    m = RE_TIME.fullmatch(text.strip())
    if not m:
        return None
    h, mi, s, ms = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + s + ms / 1000


def concept_length(expr):
    # atoms and constructors count 1 each, numbers don't
    tokens = re.findall(r"integer\[[^\]]*\]|[A-Za-z_][A-Za-z0-9_]*|\d+", expr)
    length = 0
    for tok in tokens:
        if tok.startswith("integer["):
            length += 1
        elif tok in ("some", "only", "min", "max", "exactly"):
            length += 1
        elif tok.isdigit():
            length += 0
        else:
            length += 1
    return length


def parse_log(run_id, text):
    sols, anytime = [], []
    run = {"run_id": run_id, "status": "unknown"}
    in_solutions = False
    for line in text.splitlines():
        m = RE_REASONER.search(line)
        if m:
            run["reasoner_init_s"] = parse_duration(m.group(1))
        m = RE_IMPROVE.search(line)
        if m:
            anytime.append({"run_id": run_id, "train_acc": float(m.group(1)) / 100,
                            "after_s": parse_duration(m.group(2)) if m.group(2) else None,
                            "concept": m.group(3).strip()})
        m = RE_TERMINATED.search(line)
        if m:
            run.update(status="terminated", search_time_s=parse_duration(m.group(1)),
                       descriptions_tested=int(m.group(2)), search_tree_nodes=int(m.group(3)))
        m = RE_OCEL_STOP.search(line)
        if m:
            run.update(status="terminated", descriptions_tested=int(m.group(1)))
        if line.startswith("solutions"):
            in_solutions = True
            continue
        if in_solutions:
            m = RE_CELOE_SOL.match(line)
            if m:
                sols.append({"run_id": run_id, "rank": int(m.group(1)), "concept": m.group(2),
                             "train_acc": float(m.group(3)) / 100,
                             "train_f1": float(m.group(4)) / 100,
                             "length": concept_length(m.group(2))})
                continue
            m = RE_OCEL_SOL.match(line)
            if m:
                sols.append({"run_id": run_id, "rank": int(m.group(1)), "concept": m.group(2),
                             "train_acc": float(m.group(3)) / 100, "train_f1": None,
                             "length": int(m.group(4))})
                continue
            if line.strip() == "" and sols:
                in_solutions = False
    if "Exception" in text and not sols:
        run["status"] = "error"
    if not sols and anytime:
        # OCEL prints no solution list when the noise target isn't met
        last = anytime[-1]
        sols.append({"run_id": run_id, "rank": 1, "concept": last["concept"],
                     "train_acc": last["train_acc"], "train_f1": None,
                     "length": concept_length(last["concept"])})
        run["note"] = "no solution within noise; best expression found reported"
    if sols:
        best = sols[0]
        run.update(best_concept=best["concept"], best_train_acc=best["train_acc"],
                   best_train_f1=best["train_f1"], best_length=best["length"],
                   n_solutions=len(sols))
    run["n_improvements"] = len(anytime)
    return run, sols, anytime


def conf_metadata(conf_path):
    meta = {}
    head = conf_path.read_text(encoding="utf-8").splitlines()[:5]
    for line in head:
        for key, pat in (("kb", r"KB: (\S+)"), ("algorithm", r"algorithm: (\S+)"),
                         ("language", r"language: (\S+)"), ("time_budget_s", r"time: (\d+)s"),
                         ("max_depth", r"max_depth: (\d+)"), ("noise", r"noise: (\d+)%"),
                         ("expansion_penalty", r"expansion penalty: ([\d.]+)"),
                         ("accuracy_method", r"accuracy method: (\S+)"), ("group", r"group: ([\w-]+)")):
            m = re.search(pat, line)
            if m:
                meta[key] = m.group(1)
    return meta


def run_one(conf, java, dl_home, heap):
    log_path = LOG_DIR / f"{conf.stem}.log"
    cmd = [java, f"-Xmx{heap}", *ADD_OPENS,
           f"-Dlog4j.configuration=file:{(dl_home / 'etc' / 'log4j.properties').as_posix()}",
           "-cp", str(dl_home / "lib" / "*"), "org.dllearner.cli.CLI", str(conf)]
    t0 = time.time()
    with log_path.open("w", encoding="utf-8") as log:
        log.write("# " + " ".join(cmd) + "\n")
        proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=str(dl_home))
    wall = time.time() - t0
    return log_path, wall, proc.returncode


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dl-learner", type=Path,
                    default=Path(os.environ.get("DLLEARNER_HOME",
                                                ROOT / "tools" / "dl-learner" / "dllearner-1.5.0")))
    ap.add_argument("--java", default=os.environ.get("JAVA", "java"))
    ap.add_argument("--heap", default="4g")
    ap.add_argument("--only", nargs="*", default=None, help="conf name prefixes to run")
    ap.add_argument("--parse-only", action="store_true")
    args = ap.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    confs = sorted(CONF_DIR.glob("*.conf"))
    if args.only:
        confs = [c for c in confs if any(c.stem.startswith(p) for p in args.only)]
    if not confs:
        sys.exit("no .conf files selected")

    runs, sols, anytime = [], [], []
    for conf in confs:
        log_path = LOG_DIR / f"{conf.stem}.log"
        wall = None
        if not args.parse_only:
            if not (args.dl_learner / "lib").exists():
                sys.exit(f"DL-Learner not found at {args.dl_learner}")
            print(f"[{time.strftime('%H:%M:%S')}] running {conf.stem} ...", flush=True)
            log_path, wall, rc = run_one(conf, args.java, args.dl_learner, args.heap)
            print(f"    done in {wall:.0f}s (exit {rc})", flush=True)
        if not log_path.exists():
            print(f"    no log for {conf.stem}, skipped")
            continue
        run, s, a = parse_log(conf.stem, log_path.read_text(encoding="utf-8", errors="replace"))
        run.update(conf_metadata(conf))
        if wall is not None:
            run["wall_time_s"] = round(wall, 1)
        runs.append(run)
        sols += s
        anytime += a
        if run.get("best_concept"):
            print(f"    best: {run['best_concept']}  acc={run['best_train_acc']:.3f}")

    pd.DataFrame(runs).to_csv(TABLES / "dl_runs.csv", index=False)
    pd.DataFrame(sols).to_csv(TABLES / "dl_solutions.csv", index=False)
    pd.DataFrame(anytime).to_csv(TABLES / "dl_anytime.csv", index=False)
    print(f"\n{len(runs)} runs, {len(sols)} solutions, {len(anytime)} improvement events written to {TABLES}")


if __name__ == "__main__":
    main()
