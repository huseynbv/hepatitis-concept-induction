"""Build the Hepatitis OWL knowledge base from the processed CSV files.

Modelling (see docs/dataset_analysis.md and docs/modelling_choices.md):
  * dispat rows  -> Patient individuals        (patient_<m_id>)
  * Bio rows     -> BioProfile individuals     (bio_<b_id>)
  * indis rows   -> LabRecord individuals      (lab_<in_id>)
  * inf rows     -> DurationRecord individuals (duration_<a_id>)
  * rel11/12/13  -> object properties hasBioProfile / hasLabRecord / hasDurationRecord
  * every categorical code -> a value class (e.g. GOT_3 subClassOf LabRecord) and
    an integer data property (e.g. gotCode = 3) so ordinal thresholds are expressible
  * the target column dispat.Type is NEVER written to the ontology; it is exported
    separately to data/processed/labels.csv

Variants (command-line flags):
  --disjoint            add pairwise disjointness between the four entity classes and
                        between sibling value classes of the same attribute (v2)
  --closure             add per-patient role closure axioms (hasX only {linked...} and
                        hasX max 0 when no link) so universal restrictions are entailed
                        under the open-world assumption
  --exclude-inf         drop DurationRecord individuals and hasDurationRecord links
                        (artefact ablation)
  --no-data-properties  drop the integer data properties (smaller ABox)
  --train-only          keep only the patients listed in configs/folds/train.csv
  --output PATH         output file (default ontology/hepatitis.owl)
  --no-labels           do not (re)write data/processed/labels.csv

Running without flags reproduces the original ontology/hepatitis.owl (v1).
"""
from pathlib import Path
import argparse
import types

import pandas as pd
from owlready2 import (
    get_ontology,
    Thing,
    ObjectProperty,
    DataProperty,
    AllDisjoint,
    OneOf,
)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "processed"
ONTOLOGY_DIR = ROOT / "ontology"
IRI = "http://example.org/hepatitis.owl"

LAB_ATTRIBUTES = ["got", "gpt", "alb", "tbil", "dbil", "che", "ttt", "ztt", "tcho", "tp"]


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--output", type=Path, default=ONTOLOGY_DIR / "hepatitis.owl")
    p.add_argument("--disjoint", action="store_true")
    p.add_argument("--closure", action="store_true")
    p.add_argument("--exclude-inf", action="store_true")
    p.add_argument("--no-data-properties", action="store_true")
    p.add_argument("--train-only", action="store_true")
    p.add_argument("--no-labels", action="store_true")
    return p.parse_args()


def load_tables():
    t = {
        "bio": pd.read_csv(DATA_DIR / "Bio.csv"),
        "patients": pd.read_csv(DATA_DIR / "dispat.csv"),
        "labs": pd.read_csv(DATA_DIR / "indis.csv"),
        "durations": pd.read_csv(DATA_DIR / "inf.csv"),
        "rel_bio": pd.read_csv(DATA_DIR / "rel11.csv"),
        "rel_labs": pd.read_csv(DATA_DIR / "rel12.csv"),
        "rel_durations": pd.read_csv(DATA_DIR / "rel13.csv"),
    }
    for name in ("patients", "bio", "labs", "durations"):
        assert not t[name].isnull().any().any(), f"{name} has missing values"
    assert t["patients"]["m_id"].is_unique and t["bio"]["b_id"].is_unique
    assert t["labs"]["in_id"].is_unique and t["durations"]["a_id"].is_unique
    assert len(t["patients"]) == 500 and len(t["bio"]) == 32
    assert len(t["labs"]) == 5691 and len(t["durations"]) == 196
    assert set(t["rel_bio"]["m_id"]) <= set(t["patients"]["m_id"])
    assert set(t["rel_bio"]["b_id"]) <= set(t["bio"]["b_id"])
    assert set(t["rel_labs"]["m_id"]) <= set(t["patients"]["m_id"])
    assert set(t["rel_labs"]["in_id"]) <= set(t["labs"]["in_id"])
    assert set(t["rel_durations"]["m_id"]) <= set(t["patients"]["m_id"])
    assert set(t["rel_durations"]["a_id"]) <= set(t["durations"]["a_id"])
    for name in ("rel_bio", "rel_labs", "rel_durations"):
        assert not t[name].duplicated().any(), f"{name} has duplicate links"
    return t


def restrict_to_patients(t, keep_ids):
    """Keep only the given patients and the records reachable from them."""
    keep = set(keep_ids)
    t["patients"] = t["patients"][t["patients"]["m_id"].isin(keep)]
    t["rel_bio"] = t["rel_bio"][t["rel_bio"]["m_id"].isin(keep)]
    t["rel_labs"] = t["rel_labs"][t["rel_labs"]["m_id"].isin(keep)]
    t["rel_durations"] = t["rel_durations"][t["rel_durations"]["m_id"].isin(keep)]
    t["bio"] = t["bio"][t["bio"]["b_id"].isin(t["rel_bio"]["b_id"])]
    t["labs"] = t["labs"][t["labs"]["in_id"].isin(t["rel_labs"]["in_id"])]
    t["durations"] = t["durations"][t["durations"]["a_id"].isin(t["rel_durations"]["a_id"])]
    return t


def build(t, args):
    onto = get_ontology(IRI)
    data_props = not args.no_data_properties
    include_inf = not args.exclude_inf

    with onto:
        class Patient(Thing):
            pass

        class BioProfile(Thing):
            pass

        class LabRecord(Thing):
            pass

        class hasBioProfile(ObjectProperty):
            domain = [Patient]
            range = [BioProfile]

        class hasLabRecord(ObjectProperty):
            domain = [Patient]
            range = [LabRecord]

        entity_classes = [Patient, BioProfile, LabRecord]
        DurationRecord = hasDurationRecord = None
        if include_inf:
            class DurationRecord(Thing):
                pass

            class hasDurationRecord(ObjectProperty):
                domain = [Patient]
                range = [DurationRecord]

            entity_classes.append(DurationRecord)

        # Data properties (integer codes).
        props = {}
        if data_props:
            spec = [("sexCode", Patient), ("ageCode", Patient),
                    ("fibrosisCode", BioProfile), ("activityCode", BioProfile)]
            if include_inf:
                spec.append(("durationCode", DurationRecord))
            spec += [(f"{c}Code", LabRecord) for c in LAB_ATTRIBUTES]
            for name, dom in spec:
                prop = types.new_class(name, (DataProperty,))
                prop.domain = [dom]
                prop.range = [int]
                props[name] = prop

        # Value classes, grouped by attribute so disjointness can be declared per group.
        groups = {}

        def value_group(prefix, parent, codes):
            classes = []
            for code in sorted(int(c) for c in codes):
                classes.append(types.new_class(f"{prefix}_{code}", (parent,)))
            groups[prefix] = classes
            return {int(c.name.split("_")[-1]): c for c in classes}

        sex_cls = value_group("Sex", Patient, t["patients"]["sex"].unique())
        age_cls = value_group("Age", Patient, t["patients"]["age"].unique())
        fib_cls = value_group("Fibrosis", BioProfile, t["bio"]["fibros"].unique())
        act_cls = value_group("Activity", BioProfile, t["bio"]["activity"].unique())
        lab_cls = {c: value_group(c.upper(), LabRecord, t["labs"][c].unique())
                   for c in LAB_ATTRIBUTES}
        dur_cls = (value_group("Duration", DurationRecord, t["durations"]["dur"].unique())
                   if include_inf else {})

        if args.disjoint:
            AllDisjoint(entity_classes)
            for classes in groups.values():
                if len(classes) > 1:
                    AllDisjoint(classes)

        # Individuals.
        patient_map, bio_map, lab_map, dur_map = {}, {}, {}, {}
        for _, row in t["patients"].iterrows():
            pid = int(row["m_id"])
            ind = Patient(f"patient_{pid}")
            patient_map[pid] = ind
            ind.is_a.append(sex_cls[int(row["sex"])])
            ind.is_a.append(age_cls[int(row["age"])])
            if data_props:
                ind.sexCode = [int(row["sex"])]
                ind.ageCode = [int(row["age"])]

        for _, row in t["bio"].iterrows():
            bid = int(row["b_id"])
            ind = BioProfile(f"bio_{bid}")
            bio_map[bid] = ind
            ind.is_a.append(fib_cls[int(row["fibros"])])
            ind.is_a.append(act_cls[int(row["activity"])])
            if data_props:
                ind.fibrosisCode = [int(row["fibros"])]
                ind.activityCode = [int(row["activity"])]

        for _, row in t["labs"].iterrows():
            lid = int(row["in_id"])
            ind = LabRecord(f"lab_{lid}")
            lab_map[lid] = ind
            for c in LAB_ATTRIBUTES:
                code = int(row[c])
                ind.is_a.append(lab_cls[c][code])
                if data_props:
                    setattr(ind, f"{c}Code", [code])

        if include_inf:
            for _, row in t["durations"].iterrows():
                aid = int(row["a_id"])
                ind = DurationRecord(f"duration_{aid}")
                dur_map[aid] = ind
                ind.is_a.append(dur_cls[int(row["dur"])])
                if data_props:
                    ind.durationCode = [int(row["dur"])]

        # Relationships.
        for _, row in t["rel_bio"].iterrows():
            patient_map[int(row["m_id"])].hasBioProfile.append(bio_map[int(row["b_id"])])
        for _, row in t["rel_labs"].iterrows():
            patient_map[int(row["m_id"])].hasLabRecord.append(lab_map[int(row["in_id"])])
        if include_inf:
            for _, row in t["rel_durations"].iterrows():
                patient_map[int(row["m_id"])].hasDurationRecord.append(
                    dur_map[int(row["a_id"])])

        # role closure, needed if 'only' should ever be entailed by a reasoner
        if args.closure:
            roles = [hasBioProfile, hasLabRecord] + ([hasDurationRecord] if include_inf else [])
            for ind in patient_map.values():
                for role in roles:
                    linked = list(getattr(ind, role.python_name))
                    if linked:
                        ind.is_a.append(role.only(OneOf(linked)))
                    else:
                        ind.is_a.append(role.max(0, Thing))

    # quick self-check
    assert len(patient_map) == len(t["patients"])
    assert len(bio_map) == len(t["bio"]) and len(lab_map) == len(t["labs"])
    assert sum(len(p.hasBioProfile) for p in patient_map.values()) == len(t["rel_bio"])
    assert sum(len(p.hasLabRecord) for p in patient_map.values()) == len(t["rel_labs"])
    if include_inf:
        assert len(dur_map) == len(t["durations"])
        assert sum(len(p.hasDurationRecord) for p in patient_map.values()) == len(t["rel_durations"])

    stats = {
        "patients": len(patient_map), "bio_profiles": len(bio_map),
        "lab_records": len(lab_map), "duration_records": len(dur_map),
        "value_classes": sum(len(g) for g in groups.values()),
        "data_properties": len(props),
        "disjoint_axioms": (1 + sum(1 for g in groups.values() if len(g) > 1)) if args.disjoint else 0,
    }
    return onto, stats


def main():
    args = parse_args()
    t = load_tables()

    if not args.no_labels and not args.train_only:
        labels = t["patients"][["m_id", "Type"]].copy()
        labels.columns = ["patient_id", "target"]
        labels.to_csv(DATA_DIR / "labels.csv", index=False)

    if args.train_only:
        train = pd.read_csv(ROOT / "configs" / "folds" / "train.csv")
        t = restrict_to_patients(t, train["patient_id"])

    onto, stats = build(t, args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    onto.save(file=str(args.output), format="rdfxml")

    print("ONTOLOGY GENERATED AND VALIDATED")
    for k, v in stats.items():
        print(f"  {k:18} {v}")
    print(f"  flags: disjoint={args.disjoint} closure={args.closure} "
          f"exclude_inf={args.exclude_inf} data_props={not args.no_data_properties} "
          f"train_only={args.train_only}")
    print(f"Ontology saved: {args.output}")


if __name__ == "__main__":
    main()
