"""Parser and evaluators for the class expressions DL-Learner prints.

Closed-world evaluation mimics DL-Learner's closed world reasoner (complement
for negation, vacuous 'only', asserted successors for cardinalities and data
values). Open-world evaluation adds the expression as an equivalent class and
asks HermiT which individuals are entailed to belong to it.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List, Optional, Set

ROOT = Path(__file__).resolve().parent.parent
IRI = "http://example.org/hepatitis.owl#"



@dataclass(frozen=True)
class Node:
    kind: str                      # class, top, bottom, not, and, or, some, only, card, data
    name: Optional[str] = None     # class or role / data property name
    children: tuple = ()           # sub-expressions
    n: Optional[int] = None        # cardinality bound
    op: Optional[str] = None       # min / max / exactly
    facets: tuple = ()             # ((">=", 3), ("<=", 5))

    def length(self) -> int:
        # same counting as DL-Learner
        if self.kind in ("class", "top", "bottom"):
            return 1
        if self.kind == "not":
            return 1 + self.children[0].length()
        if self.kind in ("and", "or"):
            return sum(c.length() for c in self.children) + (len(self.children) - 1)
        if self.kind in ("some", "only"):
            return 2 + self.children[0].length()
        if self.kind == "card":
            return 3 + self.children[0].length()
        if self.kind == "data":
            return 3
        raise ValueError(self.kind)

    def depth(self) -> int:
        if self.kind in ("class", "top", "bottom", "data"):
            return 1 if self.kind == "data" else 0
        if self.kind in ("some", "only", "card"):
            return 1 + self.children[0].depth()
        return max(c.depth() for c in self.children)

    def roles(self) -> Set[str]:
        out = set()
        if self.kind in ("some", "only", "card", "data"):
            out.add(self.name)
        for c in self.children:
            out |= c.roles()
        return out

    def to_manchester(self) -> str:
        if self.kind == "class":
            return self.name
        if self.kind == "top":
            return "Thing"
        if self.kind == "bottom":
            return "Nothing"
        if self.kind == "not":
            return f"not ({self.children[0].to_manchester()})"
        if self.kind in ("and", "or"):
            return f" {self.kind} ".join(
                f"({c.to_manchester()})" if c.kind in ("and", "or") else c.to_manchester()
                for c in self.children)
        if self.kind in ("some", "only"):
            return f"{self.name} {self.kind} ({self.children[0].to_manchester()})"
        if self.kind == "card":
            return f"{self.name} {self.op} {self.n} ({self.children[0].to_manchester()})"
        if self.kind == "data":
            facets = ", ".join(f"{o} {v}" for o, v in self.facets)
            return f"{self.name} some integer[{facets}]"
        raise ValueError(self.kind)



TOKEN_RE = re.compile(r"\s*(?:(integer\[[^\]]*\])|(>=|<=|>|<|,)|([()])|(\d+)|([A-Za-z_][A-Za-z0-9_]*))")


def tokenize(text: str) -> List[str]:
    tokens, pos = [], 0
    text = text.strip()
    while pos < len(text):
        m = TOKEN_RE.match(text, pos)
        if not m or m.end() == pos:
            raise ValueError(f"cannot tokenize at {pos}: {text[pos:pos+20]!r}")
        tokens.append(next(g for g in m.groups() if g is not None))
        pos = m.end()
    return tokens


class Parser:
    def __init__(self, text: str):
        self.toks = tokenize(text)
        self.i = 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def take(self, expected=None):
        tok = self.peek()
        if expected is not None and tok != expected:
            raise ValueError(f"expected {expected!r}, got {tok!r} in {' '.join(self.toks)}")
        self.i += 1
        return tok

    def parse(self) -> Node:
        node = self.disj()
        if self.peek() is not None:
            raise ValueError(f"trailing tokens: {self.toks[self.i:]}")
        return node

    def disj(self):
        parts = [self.conj()]
        while self.peek() == "or":
            self.take()
            parts.append(self.conj())
        return parts[0] if len(parts) == 1 else Node("or", children=tuple(parts))

    def conj(self):
        parts = [self.unary()]
        while self.peek() == "and":
            self.take()
            parts.append(self.unary())
        return parts[0] if len(parts) == 1 else Node("and", children=tuple(parts))

    def unary(self):
        tok = self.peek()
        if tok == "not":
            self.take()
            return Node("not", children=(self.unary(),))
        if tok == "(":
            self.take()
            node = self.disj()
            self.take(")")
            return node
        if tok == "Thing":
            self.take()
            return Node("top")
        if tok == "Nothing":
            self.take()
            return Node("bottom")
        name = self.take()
        nxt = self.peek()
        if nxt in ("some", "only"):
            self.take()
            if self.peek() is not None and (self.peek().startswith("integer")
                                            or self.peek() in ("integer", "boolean", "double")):
                dt = self.take()
                facets = self._facets(dt)
                return Node("data", name=name, facets=facets)
            return Node(nxt, name=name, children=(self.unary(),))
        if nxt in ("min", "max", "exactly"):
            self.take()
            n = int(self.take())
            return Node("card", name=name, op=nxt, n=n, children=(self.unary(),))
        return Node("class", name=name)

    @staticmethod
    def _facets(dt: str):
        m = re.fullmatch(r"integer\[(.*)\]", dt)
        if not m:
            return ()
        facets = []
        for part in m.group(1).split(","):
            op, val = part.strip().split()
            facets.append((op, int(val)))
        return tuple(facets)


def parse(text: str) -> Node:
    return Parser(text).parse()



class ClosedWorldKB:

    def __init__(self, owl_path: Path):
        from owlready2 import World
        # all KB variants have the same IRI, owlready would hand back the cached one
        self.world = World()
        self.onto = self.world.get_ontology("file://" + owl_path.resolve().as_posix()).load()
        self.individuals: Set[str] = set()
        self.classes: Dict[str, Set[str]] = {}
        self.roles: Dict[str, Dict[str, Set[str]]] = {}
        self.data: Dict[str, Dict[str, List[int]]] = {}
        for cls in self.onto.classes():
            self.classes.setdefault(cls.name, set())
        for prop in self.onto.object_properties():
            self.roles[prop.name] = {}
        for prop in self.onto.data_properties():
            self.data[prop.name] = {}
        for ind in self.onto.individuals():
            self.individuals.add(ind.name)
            for cls in ind.is_a:
                if hasattr(cls, "name"):
                    self._assert_class(cls, ind.name)
            for prop in self.onto.object_properties():
                vals = getattr(ind, prop.python_name)
                if vals:
                    self.roles[prop.name][ind.name] = {v.name for v in vals}
            for prop in self.onto.data_properties():
                vals = getattr(ind, prop.python_name)
                if vals:
                    self.data[prop.name][ind.name] = list(vals)

    def _assert_class(self, cls, ind_name):
        # also the named superclasses, like the materialised TBox in DL-Learner
        stack = [cls]
        seen = set()
        while stack:
            c = stack.pop()
            if c in seen or not hasattr(c, "name") or c.name == "Thing":
                continue
            seen.add(c)
            self.classes.setdefault(c.name, set()).add(ind_name)
            stack.extend(p for p in c.is_a if hasattr(p, "name"))

    def extension(self, node: Node) -> Set[str]:
        k = node.kind
        if k == "top":
            return set(self.individuals)
        if k == "bottom":
            return set()
        if k == "class":
            if node.name not in self.classes:
                raise KeyError(f"unknown class {node.name}")
            return set(self.classes[node.name])
        if k == "not":
            return self.individuals - self.extension(node.children[0])
        if k == "and":
            result = None
            for c in node.children:
                e = self.extension(c)
                result = e if result is None else result & e
            return result
        if k == "or":
            result = set()
            for c in node.children:
                result |= self.extension(c)
            return result
        if k in ("some", "only", "card"):
            succ = self.roles.get(node.name)
            if succ is None:
                raise KeyError(f"unknown role {node.name}")
            filler = self.extension(node.children[0])
            if k == "some":
                return {i for i, s in succ.items() if s & filler}
            if k == "only":
                return {i for i in self.individuals if succ.get(i, set()) <= filler}
            counts = {i: len(s & filler) for i, s in succ.items()}
            if node.op == "min":
                return {i for i, c in counts.items() if c >= node.n} if node.n > 0 else set(self.individuals)
            if node.op == "max":
                return {i for i in self.individuals if counts.get(i, 0) <= node.n}
            return {i for i in self.individuals if counts.get(i, 0) == node.n}
        if k == "data":
            vals = self.data.get(node.name)
            if vals is None:
                raise KeyError(f"unknown data property {node.name}")

            def ok(v):
                return all((o == ">=" and v >= b) or (o == "<=" and v <= b)
                           or (o == ">" and v > b) or (o == "<" and v < b)
                           for o, b in node.facets)
            return {i for i, vs in vals.items() if any(ok(v) for v in vs)}
        raise ValueError(k)


def metrics(predicted: Set[str], positives: Set[str], negatives: Set[str]) -> dict:
    tp = len(predicted & positives)
    fp = len(predicted & negatives)
    fn = len(positives - predicted)
    tn = len(negatives - predicted)
    n = tp + fp + fn + tn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "accuracy": (tp + tn) / n if n else 0.0,
            "precision": precision, "recall": recall, "f1": f1}



def owa_instances(owl_path: Path, node: Node, reasoner: str = "hermit",
                  timeout: int = 600) -> Set[str]:
    # loads a fresh copy, adds LearnedConcept == expr, lets the reasoner classify
    from owlready2 import (World, Thing, Not, And, Or, OneOf, ConstrainedDatatype,
                           sync_reasoner_hermit, sync_reasoner_pellet, types as owl_types)
    import owlready2

    world = World()  # same IRI problem as in ClosedWorldKB
    onto = world.get_ontology("file://" + owl_path.resolve().as_posix()).load()
    ns = onto

    def build(n: Node):
        if n.kind == "top":
            return Thing
        if n.kind == "bottom":
            return owlready2.Nothing
        if n.kind == "class":
            return ns[n.name]
        if n.kind == "not":
            return Not(build(n.children[0]))
        if n.kind == "and":
            return And([build(c) for c in n.children])
        if n.kind == "or":
            return Or([build(c) for c in n.children])
        if n.kind == "some":
            return ns[n.name].some(build(n.children[0]))
        if n.kind == "only":
            return ns[n.name].only(build(n.children[0]))
        if n.kind == "card":
            fn = {"min": ns[n.name].min, "max": ns[n.name].max, "exactly": ns[n.name].exactly}[n.op]
            return fn(n.n, build(n.children[0]))
        if n.kind == "data":
            kwargs = {}
            for o, v in n.facets:
                kwargs[{">=": "min_inclusive", "<=": "max_inclusive",
                        ">": "min_exclusive", "<": "max_exclusive"}[o]] = v
            return ns[n.name].some(ConstrainedDatatype(int, **kwargs))
        raise ValueError(n.kind)

    with onto:
        Learned = owl_types.new_class("LearnedConcept", (Thing,))
        Learned.equivalent_to.append(build(node))
        if reasoner == "pellet":
            sync_reasoner_pellet(world, infer_property_values=False, debug=0)
        else:
            sync_reasoner_hermit(world, debug=0)
    return {i.name for i in Learned.instances()}


if __name__ == "__main__":
    import argparse
    import json
    import sys

    ap = argparse.ArgumentParser(description="Parse a concept; with --owa KB, run HermiT and "
                                             "print the entailed patient instances as JSON.")
    ap.add_argument("concept", nargs="+")
    ap.add_argument("--owa", metavar="KB", help="ontology file for open-world evaluation")
    ap.add_argument("--reasoner", default="hermit", choices=["hermit", "pellet"])
    args = ap.parse_args()
    node = parse(" ".join(args.concept))
    if args.owa:
        inst = owa_instances(Path(args.owa), node, reasoner=args.reasoner)
        print(json.dumps(sorted(i for i in inst if i.startswith("patient_"))))
        sys.exit(0)
    print("parsed :", node.to_manchester())
    print("length :", node.length(), " depth:", node.depth(), " roles:", sorted(node.roles()))
