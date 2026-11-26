"""PW 5 concept-induction algorithm applied to the Hepatitis learning problem.

Faithful port of the course notebook (materials/Code.zip -> ci_DL_skeleton.ipynb):
  * concept AST classes  Top/Bottom/Atom/And/Or/Not/Exists/Forall   (Exercises 1, 7)
  * finite-interpretation (closed-world) semantics `instances`      (Exercise 7.1)
  * building_blocks / refine_ext refinement operator                 (Exercise 7)
  * score = training errors + lambda * size                         (Exercise 6.2)
  * greedy / beam search (the notebook's `greedy_search` TODO, Exercise 6) - completed here
Only two ENGINEERING changes (same results, needed for 6,223 individuals):
  * KnowledgeBase indexes successors/predecessors (the notebook scans all role pairs per call)
  * instances() is memoised
The PW 5 language needs ATOMIC concepts, so it runs on the "bins as classes" encoding
(same vocabulary as ontology/hepatitis_classes.owl: Sex0/1, AGE_k, CHE_k, GPT_k, ...).

Run:  python pw5_comparison/pw5_learner.py      -> pw5_comparison/results/*.csv
"""
import itertools
import json
import sys
import time
from functools import reduce
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from kb_eval import KB as RawKB  # noqa: E402  (only used to read the CSVs once)
from kb_eval import scores  # noqa: E402


# ============================================================ Exercise 1 / 7 : concepts
class Concept:
    def _key(self): raise NotImplementedError
    def __eq__(self, other): return type(self) is type(other) and self._key() == other._key()
    def __hash__(self): return hash((type(self).__name__, self._key()))
    def __repr__(self): return str(self)

class Top(Concept):
    def _key(self): return ()
    def __str__(self): return "TOP"

class Bottom(Concept):
    def _key(self): return ()
    def __str__(self): return "BOTTOM"

class Atom(Concept):
    def __init__(self, name): self.name = name
    def _key(self): return (self.name,)
    def __str__(self): return self.name

class And(Concept):
    def __init__(self, left, right): self.left, self.right = left, right
    def _key(self): return (self.left, self.right)
    def _flat(self):
        parts = []
        for child in (self.left, self.right):
            parts += child._flat() if isinstance(child, And) else [child]
        return parts
    def __str__(self): return "(" + " AND ".join(str(p) for p in self._flat()) + ")"

class Not(Concept):
    def __init__(self, arg): self.arg = arg
    def _key(self): return (self.arg,)
    def __str__(self): return f"NOT {self.arg}"

class Or(Concept):
    def __init__(self, left, right): self.left, self.right = left, right
    def _key(self): return (self.left, self.right)
    def __str__(self): return f"({self.left} OR {self.right})"

class Exists(Concept):
    def __init__(self, role, filler): self.role, self.filler = role, filler
    def _key(self): return (self.role, self.filler)
    def __str__(self): return f"EXISTS {self.role}.{self.filler}"

class Forall(Concept):
    def __init__(self, role, filler): self.role, self.filler = role, filler
    def _key(self): return (self.role, self.filler)
    def __str__(self): return f"FORALL {self.role}.{self.filler}"


# ============================================================ Exercise 2 : knowledge base
class KnowledgeBase:
    """Same interface as the notebook; successors/predecessors are pre-indexed."""
    def __init__(self, individuals, concepts, roles):
        self.individuals = frozenset(individuals)
        self.concepts = {k: frozenset(v) for k, v in concepts.items()}
        self.succ, self.pred = {}, {}
        for r, pairs in roles.items():
            s, p = {}, {}
            for a, b in pairs:
                s.setdefault(a, set()).add(b); p.setdefault(b, set()).add(a)
            self.succ[r], self.pred[r] = s, p
        self._cache = {}

    def extension(self, name): return self.concepts.get(name, frozenset())
    def successors(self, role, x): return self.succ.get(role, {}).get(x, set())


def instances(concept, kb):
    """Closed-world semantics on the finite interpretation (Exercise 7.1), memoised."""
    hit = kb._cache.get(concept)
    if hit is not None:
        return hit
    if isinstance(concept, Top): out = kb.individuals
    elif isinstance(concept, Bottom): out = frozenset()
    elif isinstance(concept, Atom): out = kb.extension(concept.name)
    elif isinstance(concept, And): out = instances(concept.left, kb) & instances(concept.right, kb)
    elif isinstance(concept, Or): out = instances(concept.left, kb) | instances(concept.right, kb)
    elif isinstance(concept, Not): out = kb.individuals - instances(concept.arg, kb)
    elif isinstance(concept, Exists):   # x has some r-successor in ext  <=> x is an r-predecessor of ext
        ext, pred = instances(concept.filler, kb), kb.pred.get(concept.role, {})
        out = frozenset(x for y in ext for x in pred.get(y, ()))
    elif isinstance(concept, Forall):   # vacuously true without r-successors
        ext, pred = instances(concept.filler, kb), kb.pred.get(concept.role, {})
        bad = {x for y, xs in pred.items() if y not in ext for x in xs}
        out = kb.individuals - bad
    else:
        raise TypeError(type(concept).__name__)
    kb._cache[concept] = out
    return out


# ============================================================ Exercise 7 : refinement operator
def conjuncts(C):
    if isinstance(C, And): return conjuncts(C.left) | conjuncts(C.right)
    return frozenset() if isinstance(C, Top) else frozenset({C})

def conj(parts):
    parts = sorted(parts, key=str)
    return Top() if not parts else reduce(And, parts)

def node_count(C):
    if isinstance(C, (Top, Bottom, Atom)): return 1
    if isinstance(C, Not): return 1 + node_count(C.arg)
    if isinstance(C, (And, Or)): return 1 + node_count(C.left) + node_count(C.right)
    return 1 + node_count(C.filler)

def building_blocks(atoms, roles):
    blocks = [Atom(a) for a in atoms] + [Not(Atom(a)) for a in atoms]
    blocks += [Or(Atom(a), Atom(b)) for a, b in itertools.combinations(atoms, 2)]
    for r in roles:
        blocks.append(Exists(r, Top()))
        blocks += [Exists(r, Atom(a)) for a in atoms]
        blocks += [Forall(r, Atom(a)) for a in atoms]
    return blocks

_BLOCKS = {}
def refine_ext(C, atoms, roles):
    key = (tuple(atoms), tuple(roles))
    blocks = _BLOCKS.setdefault(key, building_blocks(atoms, roles))
    parts = conjuncts(C)
    out = {conj(parts | {X}) for X in blocks if X not in parts}
    for p in parts:
        if isinstance(p, (Exists, Forall)):
            for F2 in refine_ext(p.filler, atoms, roles):
                out.add(conj((parts - {p}) | {type(p)(p.role, F2)}))
    out.discard(C)
    return out


# ============================================================ Exercise 6 : scored greedy / beam search
def errors(C, pos, neg, kb):
    ext = instances(C, kb)
    return len(pos - ext) + len(neg & ext)

def score(C, pos, neg, kb, lam):
    return errors(C, pos, neg, kb) + lam * node_count(C)

def greedy_search(kb, pos, neg, atoms, roles, beam_width=1, lam=1.0, max_steps=6, skip_empty=True):
    """Beam search over refine_ext from TOP (beam_width=1 = greedy hill climbing).
    Keeps the beam_width best refinements (lowest errors + lam*size) at each step and
    stops when a step brings no improvement of the best score (or after max_steps).
    skip_empty: discard refinements that cover no positive example."""
    t0 = time.perf_counter()
    beam = [Top()]
    best, best_sc = Top(), score(Top(), pos, neg, kb, lam)
    explored = 0
    for step in range(max_steps):
        cands = {}
        for C in beam:
            for D in refine_ext(C, atoms, roles):
                if D in cands:
                    continue
                if skip_empty and not (instances(D, kb) & pos):
                    continue
                cands[D] = score(D, pos, neg, kb, lam)
        explored += len(cands)
        if not cands:
            break
        ranked = sorted(cands.items(), key=lambda kv: (kv[1], node_count(kv[0]), str(kv[0])))
        beam = [c for c, _ in ranked[:beam_width]]
        if ranked[0][1] < best_sc:
            best, best_sc = ranked[0]
        else:
            break
    return best, best_sc, explored, time.perf_counter() - t0


# ============================================================ Hepatitis KB (bins as atomic classes)
def build_kb():
    raw = RawKB(with_therapy=False)
    concepts, roles = {}, {"hasExam": set(), "hasBiopsy": set()}
    for ind, types in raw.types.items():
        for t in types:
            concepts.setdefault(t, set()).add(ind)
    for s, props in raw.obj.items():
        for r, objs in props.items():
            roles[r] |= {(s, o) for o in objs}
    atoms = sorted(c for c in concepts if c not in ("Patient", "Exam", "Biopsy"))
    return KnowledgeBase(raw.all, concepts, roles), atoms, ["hasBiopsy", "hasExam"]


if __name__ == "__main__":
    kb, atoms, roles = build_kb()
    print(f"KB: {len(kb.individuals)} individuals, {len(atoms)} atoms, "
          f"{len(building_blocks(atoms, roles))} building blocks")
    folds = json.loads((ROOT / "data" / "folds.json").read_text())
    out = Path(__file__).resolve().parent / "results"; out.mkdir(exist_ok=True)
    SETTINGS = [("greedy_lam1", 1, 1.0), ("beam5_lam1", 5, 1.0),
                ("greedy_lam5", 1, 5.0), ("beam5_lam5", 5, 5.0)]
    rows = []
    for name, bw, lam in SETTINGS:
        for f in folds:
            pos, neg = set(f["train_pos"]), set(f["train_neg"])
            C, sc, explored, secs = greedy_search(kb, pos, neg, atoms, roles, beam_width=bw, lam=lam)
            ext = instances(C, kb)
            tr = scores(ext, f["train_pos"], f["train_neg"]); te = scores(ext, f["test_pos"], f["test_neg"])
            rows.append({"setting": name, "beam_width": bw, "lambda": lam, "fold": f["fold"],
                         "concept": str(C), "size": node_count(C), "explored": explored,
                         "time_s": round(secs, 1),
                         **{f"train_{k}": v for k, v in tr.items()}, **{f"test_{k}": v for k, v in te.items()}})
            print(f"{name:12s} fold {f['fold']}  size {node_count(C):2d}  train {tr['acc']:.3f}  "
                  f"test {te['acc']:.3f}/F1 {te['f1']:.3f}  [{explored} cand, {secs:.0f}s]  {C}", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(out / "folds.csv", index=False)
    summ = df.groupby("setting", sort=False)[["train_acc", "test_acc", "test_prec", "test_rec", "test_f1",
                                              "size", "explored", "time_s"]].agg(["mean", "std"])
    summ.to_csv(out / "summary.csv")
    pd.set_option("display.width", 250)
    print(summ.round(3).to_string())
