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

## 8. Category frequency distributions

The following frequencies were queried directly from the remote database. Counts refer to records in each respective table, not necessarily unique patients.

| Attribute | Category | Frequency |
|---|---:|---:|
| sex | 0 | 355 |
| sex | 1 | 145 |
| age | 0 | 7 |
| age | 1 | 28 |
| age | 2 | 32 |
| age | 3 | 44 |
| age | 4 | 40 |
| age | 5 | 278 |
| age | 6 | 71 |
| fibros | 0 | 3 |
| fibros | 1 | 8 |
| fibros | 2 | 7 |
| fibros | 3 | 7 |
| fibros | 4 | 7 |
| activity | 0 | 2 |
| activity | 1 | 9 |
| activity | 2 | 8 |
| activity | 3 | 8 |
| activity | 4 | 5 |
| dur | 0 | 39 |
| dur | 1 | 39 |
| dur | 2 | 39 |
| dur | 3 | 39 |
| dur | 4 | 40 |
| got | 0 | 426 |
| got | 1 | 1,762 |
| got | 2 | 1,714 |
| got | 3 | 1,756 |
| got | 4 | 33 |
| gpt | 0 | 366 |
| gpt | 1 | 2,506 |
| gpt | 2 | 2,699 |
| gpt | 3 | 120 |
| alb | 0 | 3,970 |
| alb | 1 | 1,721 |
| tbil | 0 | 847 |
| tbil | 1 | 4,844 |
| dbil | 0 | 3,325 |
| dbil | 1 | 2,366 |
| che | 0 | 7 |
| che | 1 | 141 |
| che | 2 | 51 |
| che | 3 | 6 |
| che | 4 | 64 |
| che | 5 | 692 |
| che | 6 | 3,998 |
| che | 7 | 601 |
| che | 8 | 105 |
| che | 9 | 26 |
| ttt | 0 | 329 |
| ttt | 1 | 331 |
| ttt | 2 | 822 |
| ttt | 3 | 892 |
| ttt | 4 | 886 |
| ttt | 5 | 2,431 |
| ztt | 0 | 151 |
| ztt | 1 | 1,272 |
| ztt | 2 | 543 |
| ztt | 3 | 1,206 |
| ztt | 4 | 823 |
| ztt | 5 | 1,696 |
| tcho | 0 | 828 |
| tcho | 1 | 2,799 |
| tcho | 2 | 1,469 |
| tcho | 3 | 595 |
| tp | 0 | 866 |
| tp | 1 | 2,319 |
| tp | 2 | 1,433 |
| tp | 3 | 1,073 |

Rare categories will be retained initially rather than discarded. Their usefulness and risk of overfitting will be evaluated during concept learning.

## 9. Attribute semantics and codebook

The attribute descriptions were cross-checked against the Hepatitis
relational-learning dataset documentation.

| Table | Attribute | Description | Observed codes |
|---|---|---|---|
| dispat | sex | Patient sex | 0–1 |
| dispat | age | Age category | 0–6 |
| Bio | fibros | Fibrosis level | 0–4 |
| Bio | activity | Biopsy activity | 0–4 |
| indis | got | GOT enzyme level | 0–4 |
| indis | gpt | GPT enzyme level | 0–3 |
| indis | alb | Albumin level | 0–1 |
| indis | tbil | Total bilirubin | 0–1 |
| indis | dbil | Direct bilirubin | 0–1 |
| indis | che | Cholinesterase level | 0–9 |
| indis | ttt | TTT flocculation test | 0–5 |
| indis | ztt | ZTT flocculation test | 0–5 |
| indis | tcho | Total cholesterol | 0–3 |
| indis | tp | Total protein | 0–3 |
| inf | dur | Antibody-duration category | 0–4 |

The source documentation describes these attributes as discretized
categories. Exact clinical boundaries or meanings for individual
category codes have not been established. Therefore, the original
codes will be preserved in the ontology without assigning unsupported
clinical interpretations.

References:
- https://relational.fel.cvut.cz/dataset/Hepatitis
- https://huggingface.co/datasets/andrewcropper/ilp-datasets



## 10. Relational Structure and Cardinality Analysis

The Hepatitis_std dataset contains four entity tables (`dispat`, `Bio`, `indis`, and `inf`) and three association tables (`rel11`, `rel12`, and `rel13`).

The `dispat` table represents the 500 patients and serves as the central entity. The remaining entity tables contain additional records connected to patients through association tables.

### 10.1 Relationship Analysis

Beyond the basic relationship statistics presented in Section 4, we examined the actual links between patients and records using the locally extracted CSV files.

The analysis included:
- Number of unique patients and linked records.
- Number of records associated with each patient.
- Duplicate relationship checks.
- Foreign-key integrity checks.

All six foreign-key checks passed, and no duplicate patient-record links were found.

**Patient–Bio relationship (`rel11`)**

The association table contains 621 links between 500 patients and only 32 distinct Bio records.

Every patient is connected to at least one Bio record. However, individual Bio records can be shared by multiple patients. One Bio record is referenced by as many as 112 patients.

This is therefore a many-to-many relationship.

An important modeling consideration is that these 32 records should not be interpreted as 32 individual biopsy events. The available data does not establish that interpretation. We will use the neutral term `BioProfile` when representing these records in the ontology.

**Patient–Laboratory relationship (`rel12`)**

The association table contains 5,691 links to 5,691 distinct laboratory records.

Each laboratory record is linked to exactly one patient, while 496 patients have at least one laboratory record. The number of laboratory records per linked patient ranges from 1 to 105, with an average of approximately 11.47.

This represents a one-to-many relationship from Patient to LabRecord. Four patients have no linked laboratory record.

**Patient–Duration relationship (`rel13`)**

The association table contains 196 links between 196 patients and 196 distinct duration records.

Each linked patient has exactly one duration record. The remaining 304 patients have no linked duration record.

This represents a one-to-one relationship among the linked records, although the relationship is not present for every patient.

### 10.2 Implications for Ontology Construction

The ontology will preserve the original relational structure rather than flattening all records into patient-level attributes.

The planned representation is:

- Each row in `dispat` becomes a `Patient` individual.
- Each row in `Bio` becomes a `BioProfile` individual.
- Each row in `indis` becomes a `LabRecord` individual.
- Each row in `inf` becomes a `DurationRecord` individual.

The association tables will be represented through OWL object properties:

- `hasBioProfile`: connects patients to Bio profiles.
- `hasLabRecord`: connects patients to laboratory records.
- `hasDurationRecord`: connects patients to duration records.

Shared Bio records will be represented by the same OWL individual. This preserves the many-to-many relationship without artificially duplicating records.

Categorical attributes will be represented using classes and class assertions. For example, a Bio profile with `fibros = 3` can be asserted as an instance of `FibrosisLevel_3`.

Similarly:
- Age and sex categories will be represented on Patient individuals.
- Fibrosis and activity categories will be represented on BioProfile individuals.
- Laboratory categories will be represented on LabRecord individuals.
- Duration categories will be represented on DurationRecord individuals.

The target attribute `Type` will be excluded from the predictive ontology and maintained separately as the classification label for concept learning and evaluation. This prevents target leakage.

### 10.3 Open World Assumption Considerations

OWL follows the Open World Assumption (OWA). Under this assumption, the absence of an asserted relationship does not automatically imply that the relationship is false.

For example, a patient without an asserted `hasLabRecord` relationship cannot automatically be classified as a patient who has no laboratory records. The knowledge base may simply lack that information.

This distinction is particularly important for the four patients without laboratory links and the 304 patients without duration links.

We will consider this when defining the learning problem, interpreting learned concepts, and deciding whether closure axioms are necessary.

The ontology will initially preserve the observed relationships without assuming that missing links represent negative information.




## 11. Ontology Implementation and Validation

### 11.1 Ontology Construction

The relational Hepatitis dataset was transformed into an OWL knowledge base using Owlready2.

Four main entity classes were created:

- `Patient`
- `BioProfile`
- `LabRecord`
- `DurationRecord`

The database records were represented as OWL individuals, preserving their original identifiers. Three object properties represent the relationships between patients and their associated records:

- `hasBioProfile`
- `hasLabRecord`
- `hasDurationRecord`

Categorical attributes were represented using dedicated OWL classes. For example, patient sex and age categories are represented by classes such as `Sex_0` and `Age_4`. Similarly, fibrosis, activity, laboratory measurements, and duration categories were represented by attribute-specific classes.

Original categorical codes were also preserved through data properties, allowing the ontology to retain the source values.

### 11.2 Target Separation

The target attribute `Type` was deliberately excluded from the predictive ontology to prevent target leakage.

Instead, patient identifiers and their corresponding target labels were exported separately to `data/processed/labels.csv`.

The resulting label distribution is:

| Target code | Number of patients |
|---|---:|
| 0 | 206 |
| 1 | 294 |
| **Total** | **500** |

### 11.3 Ontology Validation

The generated ontology was independently reloaded from `ontology/hepatitis.owl` and checked against the source CSV files.

The validation confirmed:

- 500 Patient individuals.
- 32 BioProfile individuals.
- 5,691 LabRecord individuals.
- 196 DurationRecord individuals.
- 621 `hasBioProfile` relationships.
- 5,691 `hasLabRecord` relationships.
- 196 `hasDurationRecord` relationships.
- Correct preservation of categorical assertions and laboratory data-property values.
- Separation of target labels from the ontology.

### 11.4 Logical Consistency

The ontology was tested using the HermiT reasoner through Owlready2.

HermiT completed successfully in approximately 2.6 seconds without reporting any logical inconsistencies.

This confirms that the ontology is logically consistent under its current axioms. It does not, by itself, establish that all modelling assumptions are semantically correct or that the ontology has been validated against external domain knowledge.



## 12. Learning Task and Evaluation Split

### 12.1 Learning Objective

The learning task is binary concept induction over the Hepatitis OWL knowledge base.

The objective is to learn a Description Logic class expression that distinguishes patients belonging to target category 1 from patients belonging to target category 0.

The target attribute `Type` is maintained separately from the ontology. It is used only to identify positive and negative training examples and to evaluate predictions.

### 12.2 Train/Test Split

A stratified 80/20 train/test split was generated using scikit-learn's `train_test_split`, with random seed 42.

| Dataset partition | Target 0 | Target 1 | Total |
|---|---:|---:|---:|
| Training | 165 | 235 | 400 |
| Testing | 41 | 59 | 100 |
| Total | 206 | 294 | 500 |

Stratification preserves the approximate target distribution across both partitions.

The patient identifiers in the training and testing sets were verified to be disjoint.

### 12.3 Reproducibility

The split is generated by `src/create_split.py`.

The following files are produced:

- `configs/folds/train.csv`
- `configs/folds/test.csv`
- `configs/folds/split_metadata.json`

The same split will be used for DL-based concept learning and the classical machine-learning baseline to ensure a consistent evaluation protocol.
