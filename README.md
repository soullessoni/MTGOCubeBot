# MTGOCubeBot

Automatise le prêt de cartes physiques/numériques d'un Cube Magic
Online entre joueurs lors d'un draft : suivi des sessions de prêt,
distribution et récupération réelles des cartes sur MTGO, le tout
piloté depuis Discord et un dashboard web.

Gère plusieurs comptes MTGO, plusieurs cubes, et plusieurs instances
(copies physiques) d'un même cube en parallèle — chaque compte est un
simple agent de manipulation de cartes et lieu de stockage, avec son
propre pool d'inventaire et son propre verrou d'exécution (voir
[Comptes, cubes et instances](#comptes-cubes-et-instances) plus bas).

## Architecture

Trois composants qui communiquent via l'API HTTP du backend — rien
d'autre ne touche la base de données directement :

- **`backend/`** — API FastAPI + SQLite/SQLAlchemy/Alembic. Source de
  vérité pour les sessions de prêt, l'inventaire du cube, et les jobs
  MTGO. Sert aussi le dashboard statique (`backend/app/web/static/`).
- **`agent/`** — bot Discord (`discord.py`) côté joueurs et admins, et
  scripts d'automatisation du client MTGO desktop (`pywinauto`,
  Windows uniquement) pour les actions qui touchent réellement MTGO
  (créer un binder, lancer un échange, exporter la collection).
- **`ops/`** — scripts PowerShell de démarrage et de supervision
  (tâches planifiées Windows).

Toute action qui touche réellement MTGO passe par un **job** asynchrone
(`PENDING` → `RUNNING` → `SUCCEEDED`/`FAILED`) : le backend spawn un
sous-processus Python dans `agent/` qui pilote le client MTGO en temps
réel, le temps qu'un joueur accepte un échange. Chaque job est routé
vers le bon compte MTGO (variable d'environnement `MTGO_USERNAME`
injectée dans le sous-processus) et un verrou en mémoire empêche deux
jobs de piloter la même fenêtre MTGO en même temps.

## Comptes, cubes et instances

Un **`MtgoAccount`** est une simple identité de connexion MTGO (nom +
pseudo MTGO), sans notion de cube attachée. Un **`Cube`** est la
composition de référence d'un cube (importée depuis CubeCobra). Une
**`CubeInstance`** relie les deux — c'est elle qui porte réellement
l'inventaire (`InventoryItem`) et les sessions de prêt
(`LoanSession.cube_instance_id`) :

- plusieurs comptes peuvent chacun héberger un cube différent ;
- un même compte peut héberger plusieurs cubes différents ;
- un même compte peut héberger plusieurs instances du **même** cube
  (deux copies physiques suivies comme deux pools d'inventaire
  séparés, pour faire tourner deux drafts en parallèle sans se marcher
  dessus).

Gestion via le dashboard (`accounts.html`) ou l'API (`/cubes/`,
`/mtgo/accounts/`, `/mtgo/cube-instances/`). Toute session, tout job
MTGO, et l'inventaire lui-même sont scopés à une `cube_instance_id` —
voir [docs/admin-guide.md](docs/admin-guide.md) pour le détail des
endpoints.

**Limite connue** : le login MTGO (`agent/mtgo/ensure_ready.py`) reste
mono-compte pour l'instant — `agent/.env` ne porte qu'un seul
`MTGO_USERNAME`/`MTGO_PASSWORD`. Le routage des jobs vers plusieurs
comptes fonctionne dès lors que chaque compte est déjà connecté sur le
client MTGO ; la gestion des identifiants pour se connecter
automatiquement à plusieurs comptes n'est pas encore implémentée
(aucun mot de passe n'est stocké en base, par design).

## Démarrage rapide

**En un clic** (une fois les deux venvs installés, voir ci-dessous) :
double-cliquer sur [`Demarrer MTGOCubeBot.bat`](Demarrer%20MTGOCubeBot.bat)
— ouvre/connecte MTGO si besoin, démarre le backend et le bot, puis le
dashboard. Détails et supervision au démarrage de session : [ops/README.md](ops/README.md).

**Installation manuelle** :

```bash
# Backend
cd backend
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"   # Windows — .venv/bin/pip sur Linux/Mac
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m uvicorn app.main:app --reload

# Agent (bot Discord + automatisation MTGO), dans un autre terminal
cd agent
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
cp .env.example .env   # à remplir, voir agent/README.md
.venv/Scripts/python -m bot.main
```

Dashboard ensuite sur `http://localhost:8000/dashboard/`.

## Tests

Chaque composant a sa propre suite, à lancer depuis son dossier :

```bash
cd backend && .venv/Scripts/python -m pytest
cd agent && .venv/Scripts/python -m pytest
```

L'automatisation MTGO elle-même (`agent/mtgo/client.py` et les scripts
qui l'utilisent) n'est pas unit-testée — elle pilote un vrai client
MTGO desktop et n'a de sens qu'en conditions réelles.

## Documentation

- [docs/admin-guide.md](docs/admin-guide.md) ([English](docs/admin-guide.en.md)) —
  guide d'administration : dashboard, commandes Discord, configuration,
  fiabilité en production.
- [backend/README.md](backend/README.md), [agent/README.md](agent/README.md),
  [agent/mtgo/README.md](agent/mtgo/README.md) — détails techniques par
  composant.
- [ops/README.md](ops/README.md) — démarrage en un clic vs. supervision
  automatique (tâches planifiées Windows), et pourquoi pas un service
  Windows classique.
