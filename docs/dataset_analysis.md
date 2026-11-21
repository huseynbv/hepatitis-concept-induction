# Hepatitis_std Dataset Analysis

## 1. Source and task

- Dataset: Hepatitis_std
- Repository: CTU Prague Relational Learning Repository
- Source: https://relational.fel.cvut.cz/dataset/Hepatitis
- Original dataset reference: PKDD'02 Hepatitis dataset
- Task: Binary classification
- Target table: `dispat`
- Target attribute: `Type`
- Patient identifier: `m_id`

The standardized version contains 500 patients. The original dataset description mentions 690 cases; these counts refer to different dataset versions and must not be conflated.

## 2. Table statistics

| Table | Rows | Role |
|---|---:|---|
| `dispat` | 500 | Patient records and classification target |
| `Bio` | 32 | Biopsy-related records |
| `indis` | 5,691 | Laboratory-related records |
| `inf` | 196 | Duration-related records |
| `rel11` | 621 | Patient-to-Bio links |
| `rel12` | 5,691 | Patient-to-indis links |
| `rel13` | 196 | Patient-to-inf links |
| **Total** | **12,927** | |

## 3. Target distribution

| Type | Number of patients | Role |
|---|---:|---|
| 0 | 206 | Negative class |
| 1 | 294 | Positive class |
| **Total** | **500** | |

No target values are missing.

The positive/negative convention (type 1 positive, type 0 negative) is documented in an independent relational-learning description of this dataset. The exact clinical interpretation should be checked against the original dataset documentation before being stated.

## 4. Relationship statistics

| Relation | Patients linked | Total links | Min. records per linked patient | Max. records per linked patient | Average per linked patient |
|---|---:|---:|---:|---:|---:|
| `rel11` | 500 | 621 | 1 | 5 | 1.24 |
| `rel12` | 496 | 5,691 | 1 | 105 | 11.47 |
| `rel13` | 196 | 196 | 1 | 1 | 1.00 |

Patients without linked records:

- Bio records: 0
- Laboratory records: 4
- Duration records: 304

The absence of a relationship in the knowledge base will not be interpreted as evidence that the corresponding clinical attribute is zero or false.

## 5. Attribute value inspection

The following attributes were inspected. All have zero SQL NULL values in their respective tables.

| Attribute | Distinct codes observed |
|---|---|
| `dispat.sex` | 0, 1 |
| `dispat.age` | 0–6 |
| `Bio.fibros` | 0–4 |
| `Bio.activity` | 0–4 |
| `inf.dur` | 0–4 |
| `indis.got` | 0–4 |
| `indis.gpt` | 0–3 |
| `indis.alb` | 0–1 |
| `indis.tbil` | 0–1 |
| `indis.dbil` | 0–1 |
| `indis.che` | 0–9 |
| `indis.ttt` | 0–5 |
| `indis.ztt` | 0–5 |
| `indis.tcho` | 0–3 |
| `indis.tp` | 0–3 |

The values are stored as VARCHAR fields but appear to be discretized categorical codes. They will not be treated as raw continuous measurements.

## 6. Preliminary ontology design considerations

- Represent each patient in `dispat` as a patient individual.
- Represent biopsy, laboratory, and duration records as separate individuals.
- Represent the three association tables using object properties.
- Represent observed categorical codes using categorical concepts or equivalent class assertions.
- Keep the target label separate from predictive features to prevent target leakage.
- Preserve the distinction between an absent relationship and a known negative or zero value.
- Verify code meanings and value distributions before assigning semantic labels to categories.

## 7. Data provenance

The SQL dump used for this project is stored at:

`data/raw/Hepatitis_std.sql`

The database was exported from the CTU Prague MariaDB server. Table counts and target statistics were checked against the remote database.

Additional relational-learning description:
https://huggingface.co/datasets/andrewcropper/ilp-datasets

This document records observed facts and preliminary modelling decisions. It will be updated as further data inspection and ontology design are completed.
