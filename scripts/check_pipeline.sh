#!/usr/bin/env bash
# Vérifie que chaque ville de config/<env>.yaml a reçu des données récentes dans PostgreSQL et MongoDB.
# Usage : scripts/check_pipeline.sh <env> [délai_max_en_secondes]
set -euo pipefail
ENV_NAME=${1:?Usage : check_pipeline.sh <env> [délai]}
TIMEOUT=${2:-300}
COMPOSE=${COMPOSE:-docker compose}
PYTHON=${PYTHON:-python}

EXPECTED=$($PYTHON -c "import yaml; print(len(yaml.safe_load(open('config/$ENV_NAME.yaml'))['cities']))")
echo "Villes attendues : $EXPECTED"
deadline=$(( $(date +%s) + TIMEOUT ))

while true; do
  pg=$($COMPOSE exec -T postgres psql -U "$PG_USER" -d "$PG_DB" -tAc "SELECT count(DISTINCT city) FROM weather_measurements WHERE ingested_at > now() - interval '30 minutes'" 2>/dev/null || echo 0)
  mg=$($COMPOSE exec -T mongo mongosh --quiet -u "$MONGO_USER" -p "$MONGO_PASSWORD" --authenticationDatabase admin --eval 'db.getSiblingDB("meteo").weather_raw.distinct("city", {collected_at: {$gte: new Date(Date.now() - 1800000).toISOString()}}).length' 2>/dev/null || echo 0)
  echo "PostgreSQL : ${pg} ville(s) | MongoDB : ${mg} ville(s)"
  if [ "${pg:-0}" -ge "$EXPECTED" ] && [ "${mg:-0}" -ge "$EXPECTED" ]; then
    echo "OK : le pipeline fonctionne."
    exit 0
  fi
  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "ECHEC : données absentes après ${TIMEOUT}s." >&2
    exit 1
  fi
  sleep 10
done
