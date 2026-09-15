#!/usr/bin/env bash
# ============================================================
# Generates synthetic patient data using Synthea
# (https://github.com/synthetichealth/synthea), an open-source
# synthetic patient population simulator maintained by MITRE.
#
# Output: CSV files in ./output/csv/, which the ETL pipeline
# expects to find copied into data/raw/.
#
# Requires: Java 11+ (OpenJDK is fine)
# ============================================================
set -e

POPULATION=${1:-300}
STATE=${2:-Virginia}
JAR_URL="https://github.com/synthetichealth/synthea/releases/download/master-branch-latest/synthea-with-dependencies.jar"
JAR_PATH="synthea-with-dependencies.jar"

if [ ! -f "$JAR_PATH" ]; then
    echo "Downloading Synthea..."
    curl -L -o "$JAR_PATH" "$JAR_URL"
fi

echo "Generating $POPULATION synthetic patients for $STATE..."
java -jar "$JAR_PATH" \
    -p "$POPULATION" \
    --exporter.csv.export=true \
    --exporter.fhir.export=false \
    --exporter.hospital.fhir.export=false \
    --exporter.practitioner.fhir.export=false \
    --exporter.years_of_history=10 \
    "$STATE"

mkdir -p data/raw
cp output/csv/*.csv data/raw/
echo "Done. Raw CSVs copied to data/raw/"
