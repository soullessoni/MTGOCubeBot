# MTGOCubeBot — backend

API FastAPI, source de vérité pour les sessions de prêt, l'inventaire
du cube, et les jobs MTGO. Sert aussi le dashboard statique
(`app/web/static/`). Le bot Discord (`../agent`) et les scripts
d'automatisation MTGO ne touchent jamais la base directement — tout
passe par cette API.

## Installation

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"   # Windows — .venv/bin/pip sur Linux/Mac
.venv/Scripts/python -m alembic upgrade head
```

## Lancer le backend

```bash
.venv/Scripts/python -m uvicorn app.main:app --reload
```

Dashboard sur `http://localhost:8000/dashboard/`, API sous `/loan/`,
`/inventory/`, `/mtgo/` (voir `app/api/`).

Deux variables d'environnement optionnelles pilotent les jobs MTGO
(pas de fichier `.env` côté backend, lues directement dans
l'environnement du process) : `MTGO_AGENT_DIR` (dossier `../agent`,
détecté par défaut) et `MTGO_AGENT_PYTHON` (interpréteur de son venv,
détecté par défaut aussi). `DISCORD_ADMIN_WEBHOOK_URL` active les
notifications proactives en cas d'échec de job — voir
[docs/admin-guide.md](../docs/admin-guide.md).

## Tests

```bash
.venv/Scripts/python -m pytest
```

Certains tests (`tests/test_cubecobra_import.py`,
`tests/integration/test_cubecobra_export.py`, marqués `integration`)
font un vrai appel réseau vers cubecobra.com — pour les exclure :

```bash
.venv/Scripts/python -m pytest -m "not integration"
```

## Migrations

```bash
.venv/Scripts/python -m alembic revision -m "description"   # nouvelle migration
.venv/Scripts/python -m alembic upgrade head                # appliquer
.venv/Scripts/python -m alembic downgrade -1                # annuler la dernière
```

Toute nouvelle migration doit être vérifiée (upgrade **et** downgrade)
sur une copie de `cubebot.db` avant d'être appliquée à la vraie base.

## Scripts (`scripts/`)

- `backup_db.py [--keep N]` — copie `cubebot.db` vers `backups/` avec
  horodatage, purge les anciennes sauvegardes au-delà de la rétention.
- `import_inventory_from_dek.py <chemin.dek>` — (re)peuple la table
  d'inventaire depuis un vrai export MTGO "Full Trade List".
- `check_cubecobra_export.py` — utilitaire de vérification manuelle,
  affiche le début d'un export CubeCobra réel.
