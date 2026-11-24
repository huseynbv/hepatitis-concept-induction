"""Step 2 - Convert the Hepatitis_std relational tables into an OWL ontology.

Modelling choices (documented for the report):
  * Rows -> individuals:   dispat -> Patient, Bio -> Biopsy, indis -> Exam (inf -> Therapy, opt.)
  * Link tables -> object properties:
        rel11 -> hasBiopsy (Patient -> Biopsy)
        rel12 -> hasExam   (Patient -> Exam)
        rel13 -> hasTherapy (Patient -> Therapy)   ONLY with --with-therapy (leakage demo)
  * Sex (binary, nominal, meaning of 0/1 unpublished) -> atomic classes Sex0 / Sex1.
  * Ordinal bins (age, lab values, biopsy grades) -> two alternative encodings:
        --encoding datatype : functional integer data properties (e.g. gpt = 2), so
                              DL-Learner can learn thresholds such as  gpt >= 2
        --encoding classes  : one atomic class per bin (e.g. GPT_2), classic ALC style
  * The TARGET (dispat.Type) is NOT asserted in the ontology (avoids leakage); it is
    written to data/labels.csv and used only to build P / N in the .conf files.
  * Missing values: the dataset has none; 4 patients simply have no exams (no hasExam
    assertion -> under OWA that means "unknown", not "no exams").
"""
import argparse
from pathlib import Path

import pandas as pd
from owlready2 import (
    AllDisjoint, DataProperty, FunctionalProperty, ObjectProperty, Thing, get_ontology,
)

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
BASE_IRI = "http://example.org/hepatitis"

EXAM_ATTRS = ["got", "gpt", "alb", "tbil", "dbil", "che", "ttt", "ztt", "tcho", "tp"]
BIO_ATTRS = ["fibros", "activity"]


def build(encoding: str, with_therapy: bool, out: Path, patients=None) -> None:
    """patients: optional collection of m_id to keep (sub-ontology for expensive OWA reasoning)."""
    t = {n: pd.read_csv(RAW / f"{n}.csv") for n in
         ["dispat", "Bio", "indis", "inf", "rel11", "rel12", "rel13"]}
    t_full = dict(t)  # bin value sets always come from the full data (same vocabulary)
    if patients is not None:
        keep = set(patients)
        t["dispat"] = t["dispat"][t["dispat"].m_id.isin(keep)]
        for r in ("rel11", "rel12", "rel13"):
            t[r] = t[r][t[r].m_id.isin(keep)]
        t["Bio"] = t["Bio"][t["Bio"].b_id.isin(t["rel11"].b_id)]
        t["indis"] = t["indis"][t["indis"].in_id.isin(t["rel12"].in_id)]
        t["inf"] = t["inf"][t["inf"].a_id.isin(t["rel13"].a_id)]

    onto = get_ontology(f"{BASE_IRI}#")
    with onto:
        # ---------------- TBox: entity classes ----------------
        class Patient(Thing): pass
        class Biopsy(Thing): pass
        class Exam(Thing): pass
        entity_classes = [Patient, Biopsy, Exam]
        if with_therapy:
            class Therapy(Thing): pass
            entity_classes.append(Therapy)
        AllDisjoint(entity_classes)

        class Sex0(Patient): pass
        class Sex1(Patient): pass
        AllDisjoint([Sex0, Sex1])

        # ---------------- TBox: object properties (from link tables) ----------------
        class hasBiopsy(ObjectProperty):
            domain = [Patient]; range = [Biopsy]
        class hasExam(ObjectProperty):
            domain = [Patient]; range = [Exam]
        if with_therapy:
            class hasTherapy(ObjectProperty):
                domain = [Patient]; range = [Therapy]

        # ---------------- TBox: ordinal attributes ----------------
        # attribute name -> (owner class, column)
        ordinal = {"age": Patient, **{a: Biopsy for a in BIO_ATTRS},
                   **{a: Exam for a in EXAM_ATTRS}}
        if with_therapy:
            ordinal["dur"] = Therapy

        if encoding == "datatype":
            props = {}
            for attr, owner in ordinal.items():
                props[attr] = type(attr, (DataProperty, FunctionalProperty),
                                   {"namespace": onto, "domain": [owner], "range": [int]})

            def assert_ordinal(ind, attr, value):
                setattr(ind, attr, int(value))
        else:  # classes: one subclass per observed bin, bins of one attribute are disjoint
            bin_cls = {}
            for attr, owner in ordinal.items():
                values = sorted(t_full[{"age": "dispat", "dur": "inf"}.get(
                    attr, "Bio" if attr in BIO_ATTRS else "indis")][attr].unique())
                group = [type(f"{attr.upper()}_{v}", (owner,), {"namespace": onto})
                         for v in values]
                AllDisjoint(group) if len(group) > 1 else None
                bin_cls.update({(attr, v): c for v, c in zip(values, group)})

            def assert_ordinal(ind, attr, value):
                ind.is_a.append(bin_cls[(attr, int(value))])

        # ---------------- ABox ----------------
        patients = {}
        for r in t["dispat"].itertuples():
            p = Patient(f"patient_{r.m_id}")
            p.is_a.append(Sex0 if r.sex == 0 else Sex1)
            assert_ordinal(p, "age", r.age)
            patients[r.m_id] = p

        biopsies = {}
        for r in t["Bio"].itertuples():
            b = Biopsy(f"biopsy_{r.b_id}")
            for a in BIO_ATTRS:
                assert_ordinal(b, a, getattr(r, a))
            biopsies[r.b_id] = b

        exams = {}
        for r in t["indis"].itertuples():
            e = Exam(f"exam_{r.in_id}")
            for a in EXAM_ATTRS:
                assert_ordinal(e, a, getattr(r, a))
            exams[r.in_id] = e

        for r in t["rel11"].itertuples():
            patients[r.m_id].hasBiopsy.append(biopsies[r.b_id])
        for r in t["rel12"].itertuples():
            patients[r.m_id].hasExam.append(exams[r.in_id])

        if with_therapy:
            therapies = {}
            for r in t["inf"].itertuples():
                th = Therapy(f"therapy_{r.a_id}")
                assert_ordinal(th, "dur", r.dur)
                therapies[r.a_id] = th
            for r in t["rel13"].itertuples():
                patients[r.m_id].hasTherapy.append(therapies[r.a_id])

    out.parent.mkdir(parents=True, exist_ok=True)
    onto.save(file=str(out), format="rdfxml")
    n_ind = len(list(onto.individuals()))
    print(f"saved {out.relative_to(ROOT)}: {len(list(onto.classes()))} classes, "
          f"{n_ind} individuals, encoding={encoding}, therapy={with_therapy}")


def write_labels() -> None:
    """Target labels live OUTSIDE the ontology. Type 0 = Hepatitis B, 1 = Hepatitis C."""
    d = pd.read_csv(RAW / "dispat.csv")
    lab = pd.DataFrame({"individual": "patient_" + d.m_id.astype(str),
                        "type": d.Type.map({0: "B", 1: "C"})})
    lab.to_csv(ROOT / "data" / "labels.csv", index=False)
    print("saved data/labels.csv:", lab.type.value_counts().to_dict())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--encoding", choices=["datatype", "classes"], default="datatype")
    ap.add_argument("--with-therapy", action="store_true",
                    help="include interferon therapy table (LEAKAGE demonstration only)")
    a = ap.parse_args()
    name = f"hepatitis_{a.encoding}{'_therapy' if a.with_therapy else ''}.owl"
    build(a.encoding, a.with_therapy, ROOT / "ontology" / name)
    write_labels()
