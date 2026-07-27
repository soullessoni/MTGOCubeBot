# Guide d'administration — MTGOCubeBot

Ce document décrit les écrans du dashboard web et les commandes du bot
Discord utilisés pour administrer les sessions de prêt de cartes du
Cube MTGO.

## Vue d'ensemble

Le système a trois composants :

- **Le backend** (FastAPI) — source de vérité pour les sessions de
  prêt, l'inventaire, et les jobs MTGO. Sert aussi le dashboard.
- **Le dashboard** (pages statiques servies sous `/dashboard/`) —
  interface web pour consulter et piloter les sessions.
- **Le bot Discord** — interface côté joueurs (identification,
  confirmation de réception/retour) et côté admin (déclenchement des
  échanges MTGO réels).

Les actions qui touchent réellement MTGO (créer un binder, lancer un
échange, exporter la collection) passent toujours par un **job MTGO** :
une tâche de fond qui pilote le client MTGO du bot en temps réel
(plusieurs dizaines de secondes à quelques minutes, le temps qu'un
joueur accepte l'échange), suivie via son statut (`PENDING` → `RUNNING`
→ `SUCCEEDED` / `FAILED`).

## Le dashboard

Accessible à `http://<serveur>:8000/dashboard/`.

### Sessions (`index.html`)

Liste toutes les sessions de prêt : ID, statut, nombre de cartes, date
de création. Le lien "Voir" ouvre le détail d'une session.

### Détail d'une session (`session.html?id=...`)

- Le statut de la session et un bouton d'action correspondant à l'étape
  courante (marquer prête, démarrer, compléter).
- **Forcer l'arrêt** — annule la session ; toute carte non retournée
  est libérée dans l'inventaire. Irréversible, demande confirmation.
- Le tableau des cartes assignées, avec pour chacune un bouton
  correspondant à son statut (préparer, distribuer, confirmer, marquer
  retournée). Ce sont des actions manuelles côté suivi — elles ne
  déclenchent aucune action MTGO réelle (voir la page Administration
  MTGO pour ça).

### Inventaire (`inventory.html`)

Liste des cartes du cube avec la quantité possédée et la quantité
disponible (possédée moins ce qui est actuellement en prêt). La
quantité possédée peut être corrigée directement.

### Administration MTGO (`mtgo.html`)

Le panneau qui déclenche les vraies actions sur le client MTGO du bot.

**Contrôles de déclenchement :**

| Action | Ce qu'elle fait |
|---|---|
| Déclencher la distribution | Crée (ou met à jour) le binder MTGO d'une session avec les cartes `PREPARED` de chaque joueur identifié. Le joueur récupère ensuite les cartes lui-même via Search Tools/Import Deck sur son propre client. |
| Déclencher la récupération | Envoie une demande d'échange au joueur MTGO indiqué, attend qu'il accepte, puis récupère toutes ses cartes `CONFIRMED` pour cette session. |
| Vérifier l'intégrité du cube | Compare la collection réelle du bot sur MTGO à l'inventaire de référence (en tenant compte de ce qui est actuellement en prêt), et remonte tout écart. Action en lecture seule, sans risque. |

**Tableau des jobs récents** : se met à jour automatiquement toutes les
5 secondes. Chaque ligne montre l'ID, le type, le statut, la session/le
joueur concerné, et un bouton "Détails".

**Détail d'un job** : affiche le journal en direct (`log_output`)
pendant qu'il tourne, puis une fois terminé :
- Pour une **récupération** : s'il manque des cartes (`still_owed`) ou
  qu'il y a un excédent reçu (`to_give_back`), un bouton de rattrapage
  apparaît :
  - **Relancer la récupération** — relance un job de récupération
    identique ; comme seules les cartes encore `CONFIRMED` sont reprises,
    ça ne redemande que ce qui manque encore.
  - **Rendre l'excédent** — crée un binder pour rendre au joueur les
    copies reçues en trop. Demande confirmation (action réelle sur MTGO).
- Pour une **vérification d'intégrité** : liste simplement ce qui
  manque ou ce qui est en trop par rapport à la référence — pas
  d'action de rattrapage automatique proposée (un écart d'intégrité a
  besoin d'un examen humain).

## Le bot Discord

### Côté joueur

1. Un admin lance `/draft-session <id>` : crée un salon
   `draft-session-<id>` dans la catégorie configurée
   (`DISCORD_CATEGORY_NAME`), avec un message listant les joueurs
   concernés et un menu déroulant pour que chacun sélectionne son nom.
2. Le joueur choisit son nom → une fenêtre modale lui demande son
   pseudo MTGO exact.
3. Une fois soumis, le bot lui envoie en message privé la liste
   complète de ses cartes, puis un message par statut regroupant les
   cartes concernées avec un seul bouton d'action pour toutes à la
   fois (accord au singulier/pluriel selon le nombre de cartes) :
   - `DISTRIBUTED` → **J'ai reçu ces cartes** (passe en `CONFIRMED`)
   - `CONFIRMED` → **J'ai rendu ces cartes** (passe en `RETURNED`)
4. Un bouton **Corriger mon pseudo MTGO** reste disponible si le joueur
   s'est trompé — le soumettre relie à nouveau ses cartes et renvoie
   une liste fraîche.

Les salons de session sont supprimés automatiquement une fois la
session `COMPLETED` ou `CANCELLED` (vérifié toutes les
`CLEANUP_INTERVAL_MINUTES`).

### Côté admin

Toutes les commandes suivantes sont réservées aux membres ayant la
permission Discord **Administrateur**, ou un rôle nommé exactement
**`Admin`** sur le serveur. Une tentative par un membre non autorisé
reçoit un message "Réservé aux admins." au lieu d'échouer silencieusement.

| Commande | Effet |
|---|---|
| `/mtgo-give <session_id>` | Équivalent Discord du bouton "Déclencher la distribution" du dashboard. |
| `/mtgo-return <session_id> <mtgo_username>` | Équivalent du bouton "Déclencher la récupération". |
| `/mtgo-integrity-check` | Équivalent du bouton "Vérifier l'intégrité du cube". |
| `/mtgo-job-status <job_id>` | Consulte le statut et les dernières lignes de journal d'un job en cours ou passé — utile si on a fermé la notification initiale ou si le bot a redémarré pendant l'attente. |

Après un déclenchement (`/mtgo-give`, `/mtgo-return`,
`/mtgo-integrity-check`), le bot répond immédiatement avec le numéro du
job, puis revient de lui-même avec le résultat une fois le job terminé
(pas besoin de relancer `/mtgo-job-status` à la main, sauf si on veut
vérifier plus tard). Une récupération qui remonte un écart affiche les
mêmes boutons de rattrapage ("Relancer la récupération" /
"Rendre l'excédent") que dans le dashboard.

## Configuration requise

**Bot Discord** (`agent/.env`) :

| Variable | Rôle |
|---|---|
| `DISCORD_BOT_TOKEN` | Obligatoire — token du bot. |
| `DISCORD_GUILD_ID` | Optionnel — limite les commandes à un serveur précis (sync instantané) plutôt qu'une propagation globale (jusqu'à 1h). |
| `BACKEND_API_URL` | URL du backend, `http://localhost:8000` par défaut. |
| `DISCORD_CATEGORY_NAME` | Catégorie où créer les salons de session, `Automated Draft on MTGO` par défaut. |
| `CLEANUP_INTERVAL_MINUTES` | Fréquence de nettoyage des salons terminés, 2 minutes par défaut. |
| `MTGO_USERNAME` / `MTGO_PASSWORD` | Compte MTGO du bot, utilisé par les scripts d'automatisation. |

**Backend** (variables d'environnement du process, pas de fichier
`.env` côté backend) :

| Variable | Rôle |
|---|---|
| `MTGO_AGENT_DIR` | Dossier du projet `agent/` (contient les scripts MTGO), `<repo>/agent` par défaut. |
| `MTGO_AGENT_PYTHON` | Interpréteur Python à utiliser pour lancer les jobs MTGO, `<agent>/.venv/Scripts/python.exe` par défaut. |
| `DISCORD_ADMIN_WEBHOOK_URL` | Optionnel — URL d'un webhook Discord ; si renseignée, une notification y est postée automatiquement dès qu'un job échoue ou remonte un écart (voir « Fiabilité en production » ci-dessous). Sans elle, ces événements ne sont visibles qu'en consultant le dashboard ou `/mtgo-job-status`. |

**Discord** : créer un rôle nommé exactement `Admin` sur le serveur et
l'attribuer aux personnes autorisées à déclencher des actions MTGO —
ou leur donner la permission serveur "Administrateur".

## Peupler l'inventaire depuis un export MTGO réel

La vérification d'intégrité du cube compare la collection MTGO réelle
à la table `/inventory/` du backend — elle n'est fiable que si cette
table reflète le cube complet. Pour la (re)peupler depuis un vrai
export "Full Trade List" :

```
.venv/Scripts/python.exe scripts/import_inventory_from_dek.py <chemin-vers-le-.dek>
```

Crée les cartes manquantes, met à jour les quantités possédées pour
chaque carte présente dans l'export, et remet à zéro toute carte de
l'inventaire absente de l'export (donnée de test obsolète, carte
retirée du cube, etc.). À relancer chaque fois que la composition du
cube change.

## Fiabilité en production

### Supervision des process (démarrage auto + redémarrage)

Le dossier `ops/` contient des scripts PowerShell qui déclarent deux
tâches planifiées Windows (backend + bot Discord), avec redémarrage
automatique en cas d'échec :

```powershell
powershell -ExecutionPolicy Bypass -File ops\register_scheduled_tasks.ps1
```

**Important** : ces tâches tournent volontairement dans la session
interactive de l'utilisateur connecté (déclencheur « à l'ouverture de
session », pas « que l'utilisateur soit connecté ou non »). Un vrai
service Windows (session 0) ne peut pas piloter le client MTGO via
`pywinauto` — l'automatisation MTGO échouerait silencieusement tout en
laissant croire que le backend fonctionne. Voir `ops/README.md` pour
le détail, le rollback (`unregister_scheduled_tasks.ps1`), et comment
vérifier l'état des tâches après coup.

### Sauvegarde de la base de données

Aucune sauvegarde n'était faite jusqu'ici. Un script copie
`cubebot.db` vers `backend/backups/` avec horodatage, et supprime les
plus anciennes au-delà d'une rétention configurable (30 par défaut) :

```
.venv/Scripts/python.exe scripts/backup_db.py [--keep N]
```

À planifier quotidiennement via le Planificateur de tâches Windows :
Créer une tâche de base → déclencheur quotidien → action « Démarrer
un programme » → programme `backend\.venv\Scripts\python.exe` →
arguments `scripts\backup_db.py` → dossier de démarrage `backend\`.

### Boutons Discord persistants

Les boutons « J'ai reçu/rendu ces cartes » survivent maintenant à un
redémarrage du bot (implémentés via `discord.ui.DynamicItem`, qui
encode les identifiants directement dans le `custom_id` plutôt que
dans une fermeture Python perdue au redémarrage). Le menu de
sélection du joueur et le bouton de correction du pseudo MTGO n'ont
pas encore ce traitement — voir `agent/README.md`.

### Notification proactive en cas de problème

Si `DISCORD_ADMIN_WEBHOOK_URL` est configurée côté backend, un message
est posté automatiquement sur ce webhook dès qu'un job :
- échoue franchement (`FAILED`) ;
- ou se termine avec succès mais remonte un écart (retour incomplet,
  excédent reçu, ou écart d'intégrité du cube).

Sans cette variable, ces événements ne sont visibles qu'en consultant
le dashboard ou `/mtgo-job-status` — configurer le webhook est
recommandé avant de laisser le système tourner sans supervision
active.
