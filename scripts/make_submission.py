"""Zips what has to be handed in: report, ontologies, code, .conf files, results, docs."""
from pathlib import Path
import argparse
import zipfile

ROOT = Path(__file__).resolve().parent.parent
INCLUDE = [
    "README.md", "requirements.txt", "Makefile", "run_all.sh", "run_all.ps1",
    "report", "slides", "docs", "src", "tests", "scripts", "ontology",
    "configs", "data/processed", "data/raw", "results/tables", "results/figures", "results/logs",
]
EXCLUDE_SUFFIX = {".pyc", ".gitkeep"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "hepatitis_concept_induction.zip")
    args = ap.parse_args()
    n = 0
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as z:
        for item in INCLUDE:
            p = ROOT / item
            if not p.exists():
                print(f"  (missing, skipped) {item}")
                continue
            files = [p] if p.is_file() else [f for f in p.rglob("*") if f.is_file()]
            for f in files:
                if f.suffix in EXCLUDE_SUFFIX or "__pycache__" in f.parts:
                    continue
                z.write(f, f.relative_to(ROOT).as_posix())
                n += 1
    print(f"{n} files -> {args.out} ({args.out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
