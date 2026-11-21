# Environment Setup

## 1. Development Environment

The project was developed using Ubuntu Linux and Visual Studio Code.

| Component | Version / Configuration |
|---|---|
| Operating system | Ubuntu 26.04.1 LTS (Resolute) |
| Python | 3.14.4 (system installation) |
| Python environment | Project-specific `.venv` |
| Java | OpenJDK 25.0.5.1 |
| DL-Learner | 1.5.0 |
| OWL ontology library | Owlready2 0.51 |

The Python virtual environment isolates the project's Python dependencies from system-wide packages.

## 2. Python Dependencies

The project uses Python libraries for dataset preparation, ontology construction, data processing, machine learning, evaluation, and visualization.

The main dependencies include:

- pandas and NumPy for data manipulation.
- scikit-learn for classical machine learning and evaluation.
- Owlready2 for OWL ontology construction and reasoning.
- RDFLib for RDF-related operations.
- Matplotlib for visualization.

Dependencies are specified in the project's `requirements.txt` file.

## 3. DL-Learner Installation

DL-Learner version 1.5.0 was obtained from its official GitHub release:

https://github.com/SmartDataAnalytics/DL-Learner/releases/tag/1.5.0

The standard Linux distribution (`dllearner-1.5.0.tar.gz`) was downloaded and extracted into:

`tools/dl-learner/dllearner-1.5.0/`

The installation is kept separate from the Python virtual environment.

## 4. Java Compatibility Check

The installed Java runtime was verified using `java -version`.

The active runtime is OpenJDK 25.0.5.1, accessible through `/usr/bin/java`.

The DL-Learner command-line launcher successfully started using this runtime. However, successful CLI startup alone does not establish that ontology loading and concept-learning execution are fully compatible.

A complete ontology-loading and CELOE execution test is required before confirming end-to-end compatibility.

## 5. Reproducibility

The project maintains a fixed stratified train-test split using random seed 42.

The split files are stored in `configs/folds/`:

- `train.csv`
- `test.csv`
- `split_metadata.json`

The Python environment and DL-Learner installation are maintained separately. The DL-Learner distribution is stored locally under `tools/` and is excluded from version control.

