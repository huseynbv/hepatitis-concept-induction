#!/usr/bin/env bash
# Wrapper for DL-Learner 1.5.0 (2021) on modern Java (21):
# the --add-opens flags re-open JDK internals that DL-Learner's Jena dependency reflects into.
HERE="$(cd "$(dirname "$0")" && pwd)"
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-21-openjdk}"
export JAVA_OPTS="--add-opens java.base/java.lang.invoke=ALL-UNNAMED --add-opens java.base/java.lang=ALL-UNNAMED \
--add-opens java.base/java.util=ALL-UNNAMED --add-opens java.base/java.lang.reflect=ALL-UNNAMED $JAVA_OPTS"
exec "$HERE/dllearner-1.5.0/bin/cli" "$@"
