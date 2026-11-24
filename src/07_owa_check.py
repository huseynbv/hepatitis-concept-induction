"""Step 5 (OWA vs CWA) - Evaluate concepts learned under the closed-world assumption
with an OPEN-WORLD reasoner (HermiT via owlready2).

For each concept C we add a defined class  Q ≡ C  to the ontology, let HermiT realise
the ABox, and read off the patients that are ENTAILED to be instances of Q.
Compare with the CWA extension computed by kb_eval (what DL-Learner's closed world
reasoner assumes). Scored on all 500 patients (labels only, no learning involved).
"""
import sys
import time
from pathlib import Path

import owlready2
import pandas as pd
from owlready2 import (And, ConstrainedDatatype, Not, Nothing, Or, Thing, World,
                       sync_reasoner_hermit)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from kb_eval import KB, extension, parse, scores  # noqa: E402

owlready2.JAVA_EXE = "/usr/lib/jvm/java-21-openjdk/bin/java"
owlready2.reasoning.JAVA_MEMORY = 6000

CHECKS = {  # ontology -> concepts (top concepts from the experiment grid)
    "hepatitis_datatype.owl": [
        "hasExam some (che some integer[>= 2 , <= 5])",                                   # base
        "hasExam max 1 ((tcho some integer[<= 2]) and (ztt some integer[>= 4]))",         # penalty002
        "Sex0 and (hasBiopsy max 1 Thing) and (age some integer[<= 5])",                  # penalty001
    ],
    "hepatitis_classes.owl": [
        "AGE_1 or (hasExam some (CHE_5 and (not (TP_3))))",                               # enc_classes
        "hasExam some ((not (CHE_6)) and (not (CHE_7)))",                                 # enc_classes
    ],
    "hepatitis_datatype_therapy.owl": [
        "(hasTherapy only Nothing) and (hasBiopsy max 1 Thing)",                          # leak_therapy
        "hasTherapy only Nothing",
    ],
}


def to_owlready(node, onto):
    k = node.kind
    if k == "thing": return Thing
    if k == "nothing": return Nothing
    if k == "atom": return onto[node.name]
    if k == "not": return Not(to_owlready(node.args[0], onto))
    if k in ("and", "or"):
        parts = [to_owlready(a, onto) for a in node.args]
        return And(parts) if k == "and" else Or(parts)
    prop = onto[node.name]
    f = node.args[0]
    if f.kind == "drange":
        kw = {}
        if f.lo != float("-inf"): kw["min_inclusive"] = int(f.lo)
        if f.hi != float("inf"): kw["max_inclusive"] = int(f.hi)
        filler = ConstrainedDatatype(int, **kw)
    else:
        filler = to_owlready(f, onto)
    if k == "some": return prop.some(filler)
    if k == "only": return prop.only(filler)
    if k == "min": return prop.min(node.n, filler)
    if k == "max": return prop.max(node.n, filler)
    if k == "exactly": return prop.exactly(node.n, filler)
    raise ValueError(k)


def sample_patients(per_class: int) -> pd.DataFrame:
    lab = pd.read_csv(ROOT / "data" / "labels.csv")
    return pd.concat([g.sample(per_class, random_state=0) for _, g in lab.groupby("type")])


def check_one(owl: str, concept: str, per_class: int) -> dict:
    """Worker: one concept, one HermiT run, on the sampled sub-ontology."""
    sample = sample_patients(per_class)
    pos = list(sample[sample.type == "B"].individual); neg = list(sample[sample.type == "C"].individual)
    w = World()
    onto = w.get_ontology(f"file://{ROOT / 'ontology' / 'owa_sample' / owl}").load()
    with onto:
        Q = type("Query", (Thing,), {"namespace": onto})
        Q.equivalent_to = [to_owlready(parse(concept), onto)]
    t0 = time.time()
    with onto:
        sync_reasoner_hermit(w, infer_property_values=False, debug=0)
    owa = {i.name for i in Q.instances() if i.name.startswith("patient_")}
    so = scores(owa, pos, neg)
    return {"owa_covered": len(owa), "owa_acc": so["acc"], "owa_f1": so["f1"], "hermit_s": round(time.time() - t0, 1),
            "owa_set": sorted(owa)}


if __name__ == "__main__":
    # HermiT cannot realise the full ABox (6,223 individuals) in 30 min, so OWA reasoning
    # runs on a STRATIFIED SAMPLE of patients (+ all their exams/biopsies/therapies),
    # one concept per process with its own timeout (some concepts make HermiT explode).
    import argparse, importlib, json, subprocess
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-class", type=int, default=10, help="patients sampled per class (B and C)")
    ap.add_argument("--timeout", type=int, default=300, help="seconds per concept")
    ap.add_argument("--worker", nargs=2, metavar=("OWL", "CONCEPT"), help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.worker:
        print("RESULT " + json.dumps(check_one(a.worker[0], a.worker[1], a.per_class)))
        sys.exit()

    sample = sample_patients(a.per_class)
    pos = list(sample[sample.type == "B"].individual); neg = list(sample[sample.type == "C"].individual)
    builder = importlib.import_module("02_build_ontology")
    for owl in CHECKS:
        builder.build("classes" if "classes" in owl else "datatype", "therapy" in owl,
                      ROOT / "ontology" / "owa_sample" / owl,
                      patients=[int(i.split("_")[1]) for i in sample.individual])
    kb = KB(with_therapy=True)
    rows = []
    for owl, concepts in CHECKS.items():
        for c in concepts:
            cwa = extension(parse(c), kb) & set(sample.individual)
            sc = scores(cwa, pos, neg)
            row = {"concept": c, "ontology": owl, "cwa_covered": len(cwa), "cwa_acc": sc["acc"], "cwa_f1": sc["f1"]}
            try:
                p = subprocess.run([sys.executable, __file__, "--per-class", str(a.per_class), "--worker", owl, c],
                                   capture_output=True, text=True, timeout=a.timeout)
                res = json.loads(next(l for l in p.stdout.splitlines() if l.startswith("RESULT "))[7:])
                res["owa_subset_of_cwa"] = set(res.pop("owa_set")) <= cwa
                row.update(res)
            except subprocess.TimeoutExpired:
                subprocess.run(["pkill", "-f", "org.semanticweb.HermiT"], check=False)
                row.update({"owa_covered": None, "hermit_s": f">{a.timeout} (timeout)"})
            rows.append(row)
            print(f"CWA {row['cwa_covered']:3d} / OWA {row['owa_covered']} of {len(sample)}  [{row['hermit_s']}s]  {c}", flush=True)
    df = pd.DataFrame(rows)
    (ROOT / "results" / "owa_vs_cwa").mkdir(parents=True, exist_ok=True)
    df.to_csv(ROOT / "results" / "owa_vs_cwa" / f"owa_vs_cwa_{2 * a.per_class}patients.csv", index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 75)
    print(df.drop(columns=["ontology"]).round(3).to_string(index=False))
