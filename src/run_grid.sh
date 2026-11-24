#!/usr/bin/env bash
# Runs the full experiment grid. Runtime experiments use --jobs 1 (no CPU sharing).
cd "$(dirname "$0")/.."
PY=/home/elvinmahmudzada/anaconda3/envs/symbolic-learning/bin/python
for s in enc_classes noise10 noise50 penalty002 penalty001 leak_therapy; do
  echo ">>> $s $(date +%T)"; $PY src/05_run_experiment.py $s --jobs 5 > results/_$s.out 2>&1 || echo "FAILED $s"
done
for s in rt10 rt60 rt180; do
  echo ">>> $s $(date +%T)"; $PY src/05_run_experiment.py $s --jobs 1 > results/_$s.out 2>&1 || echo "FAILED $s"
done
echo ">>> owa_hermit $(date +%T)"; $PY src/05_run_experiment.py owa_hermit --jobs 2 > results/_owa_hermit.out 2>&1 || echo "FAILED owa_hermit"
echo ">>> DONE $(date +%T)"
