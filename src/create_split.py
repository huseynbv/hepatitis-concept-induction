
from pathlib import Path
import json

import pandas as pd
from sklearn.model_selection import train_test_split


# 1. Configuration

ROOT = Path(__file__).resolve().parent.parent

LABELS_PATH = ROOT / "data" / "processed" / "labels.csv"
OUTPUT_DIR = ROOT / "configs" / "folds"

RANDOM_SEED = 42
TEST_SIZE = 0.20

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# 2. Load and validate labels

labels = pd.read_csv(LABELS_PATH)

assert list(labels.columns) == ["patient_id", "target"]
assert len(labels) == 500
assert labels["patient_id"].is_unique
assert labels["target"].notna().all()
assert set(labels["target"].unique()) == {0, 1}

print("Original dataset:")
print(labels["target"].value_counts().sort_index())


# 3. Stratified train/test split

train, test = train_test_split(
    labels,
    test_size=TEST_SIZE,
    random_state=RANDOM_SEED,
    stratify=labels["target"],
    shuffle=True,
)

train = train.sort_values("patient_id").reset_index(drop=True)
test = test.sort_values("patient_id").reset_index(drop=True)


# 4. Validate the split

train_ids = set(train["patient_id"])
test_ids = set(test["patient_id"])

assert train_ids.isdisjoint(test_ids)
assert len(train) + len(test) == len(labels)
assert train["patient_id"].nunique() == len(train)
assert test["patient_id"].nunique() == len(test)

assert set(train["target"].unique()) == {0, 1}
assert set(test["target"].unique()) == {0, 1}


# 5. Save split files

train_path = OUTPUT_DIR / "train.csv"
test_path = OUTPUT_DIR / "test.csv"

train.to_csv(train_path, index=False)
test.to_csv(test_path, index=False)

metadata = {
    "random_seed": RANDOM_SEED,
    "test_size": TEST_SIZE,
    "stratified": True,
    "total_samples": len(labels),
    "training_samples": len(train),
    "testing_samples": len(test),
    "training_distribution": {
        str(k): int(v)
        for k, v in train["target"].value_counts().sort_index().items()
    },
    "testing_distribution": {
        str(k): int(v)
        for k, v in test["target"].value_counts().sort_index().items()
    },
}

metadata_path = OUTPUT_DIR / "split_metadata.json"

with open(metadata_path, "w") as file:
    json.dump(metadata, file, indent=4)


# 6. Print summary

print("\nSPLIT GENERATED SUCCESSFULLY")
print("----------------------------")

print(f"Random seed: {RANDOM_SEED}")
print(f"Training samples: {len(train)}")
print(f"Testing samples: {len(test)}")

print("\nTraining distribution:")
print(train["target"].value_counts().sort_index())

print("\nTesting distribution:")
print(test["target"].value_counts().sort_index())

print("\nFiles saved:")
print(train_path)
print(test_path)
print(metadata_path)

print("\nAll split validation checks passed.")
