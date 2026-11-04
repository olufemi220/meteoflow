# MétéoFlow

Collecte toutes les 15 minutes la météo de plusieurs villes françaises (API Open-Meteo) avec Apache NiFi 2,
stocke la réponse brute dans MongoDB et les mesures nettoyées dans PostgreSQL 14, consultables dans pgAdmin.

## Démarrer en local (Git Bash)

```bash
cp .env.example .env
docker compose up -d --build
```

| Service | Adresse | Identifiants |
| --- | --- | --- |
| NiFi | https://localhost:8443/nifi | admin / MeteoFlow-Dev-2026 |
| pgAdmin | http://localhost:5050 | admin@meteoflow.fr / admin |
| API simulée | http://localhost:8081/v1/forecast?latitude=48.85&longitude=2.35&current=temperature_2m | — |

Une fois le flux exporté dans `flows/meteoflow.json` :

```bash
set -a; source .env; set +a
python scripts/deploy_flow.py --env dev
scripts/check_pipeline.sh dev
```

## Configuration

- `#{...}` : paramètre NiFi (configuration), alimenté par `config/<env>.yaml`.
- `${...}` : attribut de FlowFile (donnée propre à chaque ville).
- Le flux NiFi est exporté en JSON (format natif de NiFi) ; la configuration par environnement est en YAML.

## CI/CD

- Pull Request : lint, tests unitaires, test d'intégration (stack Docker + API simulée).
- Merge sur `main` : image NiFi publiée sur GHCR, déploiement en staging.
- Tag `v*.*.*` : déploiement en production après approbation manuelle.
