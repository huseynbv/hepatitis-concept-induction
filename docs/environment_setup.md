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


## 6. DL-Learner on JDK 17+ (Windows and Linux)

DL-Learner 1.5.0 was built for Java 8. On JDK 17 and later (tested with
Oracle JDK 25.0.5 and OpenJDK 21 on Windows 11) the CLI fails while initialising
Apache Jena with `InaccessibleObjectException: module java.base does not "opens
java.lang.invoke"`. Adding the following JVM flags fixes it; `src/run_dl_learner.py`
passes them automatically:

```
--add-opens java.base/java.lang=ALL-UNNAMED
--add-opens java.base/java.lang.invoke=ALL-UNNAMED
--add-opens java.base/java.lang.reflect=ALL-UNNAMED
--add-opens java.base/java.util=ALL-UNNAMED
--add-opens java.base/java.io=ALL-UNNAMED
--add-opens java.base/java.net=ALL-UNNAMED
```

The runner invokes `org.dllearner.cli.CLI` directly with `-cp lib/*` instead of
the `bin/cli` launcher so the same command works on both platforms.

## 7. Phase-0 smoke test (end-to-end compatibility)

| Check | Result |
|---|---|
| `examples/father.conf` | solution `male and (hasChild some Thing)` in 1 s |
| `ontology/hepatitis.owl` (6,419 individuals) load + closed-world materialisation | about 3 s, 4 GB heap |
| CELOE, 20 examples, 20 s | 24k descriptions tested, role-based concepts with datatype restrictions found |
| CELOE, 400 examples, 30 s | about 20k descriptions tested |

Retrieval dominates the runtime (about 1 ms per retrieval on the full ABox).
