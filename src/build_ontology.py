
from pathlib import Path
import types

import pandas as pd
from owlready2 import (
    get_ontology,
    Thing,
    ObjectProperty,
    DataProperty,
)


# 1. Paths and input data

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "processed"
ONTOLOGY_DIR = ROOT / "ontology"

ONTOLOGY_DIR.mkdir(parents=True, exist_ok=True)

bio = pd.read_csv(DATA_DIR / "Bio.csv")
patients = pd.read_csv(DATA_DIR / "dispat.csv")
labs = pd.read_csv(DATA_DIR / "indis.csv")
durations = pd.read_csv(DATA_DIR / "inf.csv")

rel_bio = pd.read_csv(DATA_DIR / "rel11.csv")
rel_labs = pd.read_csv(DATA_DIR / "rel12.csv")
rel_durations = pd.read_csv(DATA_DIR / "rel13.csv")


# 2. Basic input validation

assert not patients.isnull().any().any()
assert not bio.isnull().any().any()
assert not labs.isnull().any().any()
assert not durations.isnull().any().any()

assert patients["m_id"].is_unique
assert bio["b_id"].is_unique
assert labs["in_id"].is_unique
assert durations["a_id"].is_unique

assert len(patients) == 500
assert len(bio) == 32
assert len(labs) == 5691
assert len(durations) == 196

# Check foreign-key references.
assert set(rel_bio["m_id"]).issubset(set(patients["m_id"]))
assert set(rel_bio["b_id"]).issubset(set(bio["b_id"]))

assert set(rel_labs["m_id"]).issubset(set(patients["m_id"]))
assert set(rel_labs["in_id"]).issubset(set(labs["in_id"]))

assert set(rel_durations["m_id"]).issubset(set(patients["m_id"]))
assert set(rel_durations["a_id"]).issubset(set(durations["a_id"]))

# Check that association tables contain no duplicate links.
assert not rel_bio.duplicated().any()
assert not rel_labs.duplicated().any()
assert not rel_durations.duplicated().any()


# 3. Create ontology and main classes

onto = get_ontology("http://example.org/hepatitis.owl")

with onto:

    class Patient(Thing):
        pass

    class BioProfile(Thing):
        pass

    class LabRecord(Thing):
        pass

    class DurationRecord(Thing):
        pass

    # Object properties
    class hasBioProfile(ObjectProperty):
        domain = [Patient]
        range = [BioProfile]

    class hasLabRecord(ObjectProperty):
        domain = [Patient]
        range = [LabRecord]

    class hasDurationRecord(ObjectProperty):
        domain = [Patient]
        range = [DurationRecord]

    # Patient data properties
    class sexCode(DataProperty):
        domain = [Patient]
        range = [int]

    class ageCode(DataProperty):
        domain = [Patient]
        range = [int]

    # BioProfile data properties
    class fibrosisCode(DataProperty):
        domain = [BioProfile]
        range = [int]

    class activityCode(DataProperty):
        domain = [BioProfile]
        range = [int]

    # DurationRecord data property
    class durationCode(DataProperty):
        domain = [DurationRecord]
        range = [int]


# 4. Create categorical classes

category_classes = {}

with onto:

    # Patient categories
    for code in sorted(patients["sex"].unique()):
        name = f"Sex_{int(code)}"
        category_classes[name] = types.new_class(name, (Patient,))

    for code in sorted(patients["age"].unique()):
        name = f"Age_{int(code)}"
        category_classes[name] = types.new_class(name, (Patient,))

    # BioProfile categories
    for code in sorted(bio["fibros"].unique()):
        name = f"Fibrosis_{int(code)}"
        category_classes[name] = types.new_class(name, (BioProfile,))

    for code in sorted(bio["activity"].unique()):
        name = f"Activity_{int(code)}"
        category_classes[name] = types.new_class(name, (BioProfile,))

    # Laboratory categories
    lab_attributes = [c for c in labs.columns if c != "in_id"]

    for column in lab_attributes:
        for code in sorted(labs[column].unique()):
            name = f"{column.upper()}_{int(code)}"
            category_classes[name] = types.new_class(name, (LabRecord,))

    # Duration categories
    for code in sorted(durations["dur"].unique()):
        name = f"Duration_{int(code)}"
        category_classes[name] = types.new_class(name, (DurationRecord,))


# 5. Create laboratory data properties

lab_data_properties = {}

with onto:

    for column in lab_attributes:
        property_name = f"{column}Code"

        prop = types.new_class(property_name, (DataProperty,))
        prop.domain = [LabRecord]
        prop.range = [int]

        lab_data_properties[column] = prop


# 6. Create individuals and category assertions

patient_map = {}
bio_map = {}
lab_map = {}
duration_map = {}

with onto:

    # Patients
    for _, row in patients.iterrows():
        patient_id = int(row["m_id"])
        patient = Patient(f"patient_{patient_id}")

        patient_map[patient_id] = patient

        patient.sexCode = [int(row["sex"])]
        patient.ageCode = [int(row["age"])]

        patient.is_a.append(
            category_classes[f"Sex_{int(row['sex'])}"]
        )
        patient.is_a.append(
            category_classes[f"Age_{int(row['age'])}"]
        )

    # Bio profiles
    for _, row in bio.iterrows():
        record_id = int(row["b_id"])
        record = BioProfile(f"bio_{record_id}")

        bio_map[record_id] = record

        record.fibrosisCode = [int(row["fibros"])]
        record.activityCode = [int(row["activity"])]

        record.is_a.append(
            category_classes[f"Fibrosis_{int(row['fibros'])}"]
        )
        record.is_a.append(
            category_classes[f"Activity_{int(row['activity'])}"]
        )

    # Laboratory records
    for _, row in labs.iterrows():
        record_id = int(row["in_id"])
        record = LabRecord(f"lab_{record_id}")

        lab_map[record_id] = record

        for column in lab_attributes:
            code = int(row[column])

            setattr(record, f"{column}Code", [code])

            category_name = f"{column.upper()}_{code}"
            record.is_a.append(category_classes[category_name])

    # Duration records
    for _, row in durations.iterrows():
        record_id = int(row["a_id"])
        record = DurationRecord(f"duration_{record_id}")

        duration_map[record_id] = record

        record.durationCode = [int(row["dur"])]
        record.is_a.append(
            category_classes[f"Duration_{int(row['dur'])}"]
        )


# 7. Create object-property relationships

with onto:

    for _, row in rel_bio.iterrows():
        patient_map[int(row["m_id"])].hasBioProfile.append(
            bio_map[int(row["b_id"])]
        )

    for _, row in rel_labs.iterrows():
        patient_map[int(row["m_id"])].hasLabRecord.append(
            lab_map[int(row["in_id"])]
        )

    for _, row in rel_durations.iterrows():
        patient_map[int(row["m_id"])].hasDurationRecord.append(
            duration_map[int(row["a_id"])]
        )


# 8. Save target labels separately

labels = patients[["m_id", "Type"]].copy()
labels.columns = ["patient_id", "target"]

labels.to_csv(DATA_DIR / "labels.csv", index=False)


# 9. Validate generated ontology

# Individual counts
assert len(patient_map) == 500
assert len(bio_map) == 32
assert len(lab_map) == 5691
assert len(duration_map) == 196

# Relationship counts
assert sum(len(p.hasBioProfile) for p in patient_map.values()) == 621
assert sum(len(p.hasLabRecord) for p in patient_map.values()) == 5691
assert sum(len(p.hasDurationRecord) for p in patient_map.values()) == 196

# Every individual has its expected category assertions.
for _, row in patients.iterrows():
    p = patient_map[int(row["m_id"])]
    assert category_classes[f"Sex_{int(row['sex'])}"] in p.is_a
    assert category_classes[f"Age_{int(row['age'])}"] in p.is_a

for _, row in bio.iterrows():
    record = bio_map[int(row["b_id"])]
    assert category_classes[f"Fibrosis_{int(row['fibros'])}"] in record.is_a
    assert category_classes[f"Activity_{int(row['activity'])}"] in record.is_a

for _, row in labs.iterrows():
    record = lab_map[int(row["in_id"])]

    for column in lab_attributes:
        code = int(row[column])
        assert category_classes[f"{column.upper()}_{code}"] in record.is_a

for _, row in durations.iterrows():
    record = duration_map[int(row["a_id"])]
    assert category_classes[f"Duration_{int(row['dur'])}"] in record.is_a

# Every relationship points to the expected individual.
for _, row in rel_bio.iterrows():
    assert bio_map[int(row["b_id"])] in (
        patient_map[int(row["m_id"])].hasBioProfile
    )

for _, row in rel_labs.iterrows():
    assert lab_map[int(row["in_id"])] in (
        patient_map[int(row["m_id"])].hasLabRecord
    )

for _, row in rel_durations.iterrows():
    assert duration_map[int(row["a_id"])] in (
        patient_map[int(row["m_id"])].hasDurationRecord
    )


# 10. Save ontology

output_path = ONTOLOGY_DIR / "hepatitis.owl"
onto.save(file=str(output_path), format="rdfxml")



# 11. Print summary

print("\nONTOLOGY GENERATED AND VALIDATED")
print("--------------------------------")
print(f"Patients:          {len(patient_map)}")
print(f"Bio profiles:      {len(bio_map)}")
print(f"Lab records:       {len(lab_map)}")
print(f"Duration records:  {len(duration_map)}")

print(f"Bio relationships:      {len(rel_bio)}")
print(f"Lab relationships:      {len(rel_labs)}")
print(f"Duration relationships: {len(rel_durations)}")

print(f"Categorical classes: {len(category_classes)}")
print(f"Lab data properties: {len(lab_data_properties)}")

print(f"\nLabels saved: {DATA_DIR / 'labels.csv'}")
print(f"Ontology saved: {output_path}")
