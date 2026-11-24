"""Parse DL-Learner class expressions (Manchester-like syntax) and evaluate them on the
Hepatitis data under the CLOSED-WORLD assumption (same semantics as DL-Learner's
"closed world reasoner"), so we can score learned concepts on held-out TEST patients.

Supported syntax (what DL-Learner prints):
  Thing | Nothing | ClassName | not (C) | C and D | C or D
  r some C | r only C | r min n C | r max n C | r exactly n C
  p some integer[>= a , <= b]   (data property with a numeric range)
  p only integer[...]
"""
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

# ---------------------------------------------------------------- knowledge base (CWA)
class KB:
    """In-memory ABox. Holds BOTH encodings (bin classes like GPT_2 and integer data values),
    so concepts learned from either ontology variant can be evaluated."""

    def __init__(self, with_therapy: bool = True):
        t = {n: pd.read_csv(RAW / f"{n}.csv") for n in
             ["dispat", "Bio", "indis", "inf", "rel11", "rel12", "rel13"]}
        self.types: dict[str, set] = {}
        self.data: dict[str, dict[str, list]] = {}
        self.obj: dict[str, dict[str, list]] = {}

        def add(ind, cls, attrs):
            self.types[ind] = {cls}
            self.data[ind] = {}
            for a, v in attrs.items():
                self.data[ind][a] = [int(v)]
                self.types[ind].add(f"{a.upper()}_{int(v)}")
            self.obj[ind] = {}

        for r in t["dispat"].itertuples():
            ind = f"patient_{r.m_id}"
            add(ind, "Patient", {"age": r.age})
            self.types[ind].add("Sex0" if r.sex == 0 else "Sex1")
        for r in t["Bio"].itertuples():
            add(f"biopsy_{r.b_id}", "Biopsy", {"fibros": r.fibros, "activity": r.activity})
        exam_cols = [c for c in t["indis"].columns if c != "in_id"]
        for r in t["indis"].itertuples(index=False):
            rd = r._asdict()
            add(f"exam_{rd['in_id']}", "Exam", {c: rd[c] for c in exam_cols})
        links = [("rel11", "hasBiopsy", "biopsy_", "b_id"), ("rel12", "hasExam", "exam_", "in_id")]
        if with_therapy:
            for r in t["inf"].itertuples():
                add(f"therapy_{r.a_id}", "Therapy", {"dur": r.dur})
            links.append(("rel13", "hasTherapy", "therapy_", "a_id"))
        for table, prop, prefix, col in links:
            for r in t[table].itertuples(index=False):
                rd = r._asdict()
                self.obj[f"patient_{rd['m_id']}"].setdefault(prop, []).append(f"{prefix}{rd[col]}")
        self.all = set(self.types)


# ---------------------------------------------------------------- AST
@dataclass
class Node:
    kind: str           # thing, nothing, atom, not, and, or, some, only, min, max, exactly, drange
    args: tuple = ()
    name: str = ""
    n: int = 0
    lo: float = float("-inf")
    hi: float = float("inf")


TOKEN = re.compile(r"\s*(\(|\)|\[|\]|,|>=|<=|>|<|-?\d+(?:\.\d+)?|[A-Za-z_][\w:#.-]*)")


def tokenize(s):
    pos, out = 0, []
    s = s.strip()
    while pos < len(s):
        m = TOKEN.match(s, pos)
        if not m:
            raise ValueError(f"cannot tokenize at: {s[pos:]!r}")
        out.append(m.group(1))
        pos = m.end()
    return out


class Parser:
    QUANT = {"some", "only", "min", "max", "exactly"}
    DTYPES = {"integer", "int", "double", "float", "decimal", "long"}

    def __init__(self, s):
        self.t, self.i = tokenize(s), 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def eat(self, tok=None):
        cur = self.peek()
        if tok is not None and cur != tok:
            raise ValueError(f"expected {tok!r}, got {cur!r} in {' '.join(self.t)}")
        self.i += 1
        return cur

    def parse(self):
        node = self.or_()
        if self.peek() is not None:
            raise ValueError(f"trailing tokens: {self.t[self.i:]}")
        return node

    def or_(self):
        parts = [self.and_()]
        while self.peek() == "or":
            self.eat(); parts.append(self.and_())
        return parts[0] if len(parts) == 1 else Node("or", tuple(parts))

    def and_(self):
        parts = [self.unary()]
        while self.peek() == "and":
            self.eat(); parts.append(self.unary())
        return parts[0] if len(parts) == 1 else Node("and", tuple(parts))

    def unary(self):
        if self.peek() == "not":
            self.eat(); return Node("not", (self.unary(),))
        return self.restriction()

    def restriction(self):
        tok = self.peek()
        if tok == "(":
            self.eat("("); node = self.or_(); self.eat(")"); return node
        name = self.eat()
        if self.peek() in self.QUANT:
            q = self.eat()
            n = int(self.eat()) if q in ("min", "max", "exactly") else 0
            filler = self.filler()
            return Node(q, (filler,), name=name, n=n)
        if name == "Thing":
            return Node("thing")
        if name == "Nothing":
            return Node("nothing")
        return Node("atom", name=name.split(":")[-1].split("#")[-1])

    def filler(self):
        if self.peek() in self.DTYPES:
            self.eat()
            lo, hi = float("-inf"), float("inf")
            if self.peek() == "[":
                self.eat("[")
                while self.peek() != "]":
                    op = self.eat(); val = float(self.eat())
                    if op in (">=", ">"): lo = val if op == ">=" else val + 1e-9
                    if op in ("<=", "<"): hi = val if op == "<=" else val - 1e-9
                    if self.peek() == ",": self.eat()
                self.eat("]")
            return Node("drange", lo=lo, hi=hi)
        if self.peek() == "(":
            self.eat("("); node = self.or_(); self.eat(")"); return node
        return self.unary()


def parse(s: str) -> Node:
    return Parser(s).parse()


# ---------------------------------------------------------------- CWA evaluation
def _dllearner_max_keeps(fillers: list, target: set, n: int) -> bool:
    """Exact replica of DL-Learner 1.5.0 ClosedWorldReasoner.getIndividualsImpl for
    'r max n C'. It is OFF BY ONE: the 'too many fillers' test runs at the top of the
    loop, so when the (n+1)-th match is the last filler the individual is wrongly kept."""
    if len(fillers) <= n:
        return True
    nr = idx = 0
    for ind in sorted(fillers):  # DL-Learner iterates a SortedSet (IRI order)
        if nr > n:
            return False
        if len(fillers) - idx + nr <= n:
            break
        if ind in target:
            nr += 1
        idx += 1
    return True


def extension(node: Node, kb: KB, dllearner_compat: bool = False) -> set:
    """Set of individuals that are instances of the concept under the closed-world assumption.
    dllearner_compat=True reproduces DL-Learner's max-cardinality bug (validation only)."""
    k = node.kind
    ext = lambda n: extension(n, kb, dllearner_compat)
    if k == "thing": return set(kb.all)
    if k == "nothing": return set()
    if k == "atom": return {i for i in kb.all if node.name in kb.types[i]}
    if k == "not": return kb.all - ext(node.args[0])
    if k == "and":
        out = ext(node.args[0])
        for a in node.args[1:]: out &= ext(a)
        return out
    if k == "or":
        out = set()
        for a in node.args: out |= ext(a)
        return out
    filler = node.args[0]
    if filler.kind == "drange":  # data property restriction
        def succ_ok(i):
            vals = kb.data[i].get(node.name, [])
            return vals, [filler.lo <= v <= filler.hi for v in vals]
    else:
        fext = ext(filler)
        if k == "max" and dllearner_compat:
            return {i for i in kb.all
                    if _dllearner_max_keeps(kb.obj[i].get(node.name, []), fext, node.n)}
        def succ_ok(i):
            vals = kb.obj[i].get(node.name, [])
            return vals, [v in fext for v in vals]
    out = set()
    for i in kb.all:
        vals, ok = succ_ok(i)
        c = sum(ok)
        if ((k == "some" and c >= 1) or (k == "only" and c == len(vals))
                or (k == "min" and c >= node.n) or (k == "max" and c <= node.n)
                or (k == "exactly" and c == node.n)):
            out.add(i)
    return out


def length(node: Node) -> int:
    """Concept length, following DL-Learner's convention: atoms/⊤/⊥ = 1, each constructor
    (¬, ⊓, ⊔) adds 1, a role/data restriction adds 2 (quantifier + property) and a
    cardinality bound +1 more; a numeric datatype facet counts 1."""
    k = node.kind
    if k in ("thing", "nothing", "atom", "drange"): return 1
    if k == "not": return 1 + length(node.args[0])
    if k in ("and", "or"): return sum(map(length, node.args)) + len(node.args) - 1
    return 2 + (1 if k in ("min", "max", "exactly") else 0) + length(node.args[0])


def scores(ext: set, pos: list, neg: list) -> dict:
    tp = sum(p in ext for p in pos); fn = len(pos) - tp
    fp = sum(n in ext for n in neg); tn = len(neg) - fp
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"acc": (tp + tn) / (len(pos) + len(neg)), "prec": prec, "rec": rec, "f1": f1,
            "tp": tp, "fp": fp, "tn": tn, "fn": fn}
