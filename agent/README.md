# MTGO CubeBot — Discord bot

Bot Discord côté joueur pour les sessions de prêt de cartes. Consomme
l'API du backend (`../backend`) via HTTP — il ne touche jamais la base
de données directement.

## Principe

- Le propriétaire du cube crée une session de prêt normalement (dashboard
  ou API), puis lance `/draft-session <id>` sur le serveur Discord.
- Le bot crée un salon dédié à la session et y poste la liste des joueurs
  concernés (jamais les cartes — c'est confidentiel).
- Chaque joueur clique sur son nom dans le salon, confirme son pseudo
  MTGO dans une fenêtre privée (modal), et reçoit ensuite sa liste de
  cartes assignées **en message privé**.
- Le pseudo MTGO n'est pas mémorisé d'une session à l'autre : il est
  reconfirmé à chaque fois.
- Chaque carte reçue en MP a un bouton d'action adapté à son statut
  (confirmer réception une fois `DISTRIBUTED`, confirmer le retour une
  fois `CONFIRMED`) — ça appelle directement l'API du backend.

Les étapes "Préparer"/"Distribuer" restent une action du propriétaire du
cube via le dashboard : le bot ne couvre que le côté joueur (confirmer
réception, confirmer retour).

## Installation

```bash
cd agent
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows
# .venv/bin/pip install -r requirements.txt     # Linux/Mac
cp .env.example .env
```

Remplir `.env` :

1. Aller sur https://discord.com/developers/applications, créer une
   application, onglet **Bot** → créer le bot → copier le token dans
   `DISCORD_BOT_TOKEN`.
2. Onglet **OAuth2 → URL Generator** : scopes `bot` + `applications.commands`,
   permissions minimum `Send Messages`, `Use Slash Commands`,
   `Manage Channels` (pour la création du salon par session). Utiliser
   l'URL générée pour inviter le bot sur le serveur cible.
3. Copier l'ID du serveur (clic droit sur son icône → Copier
   l'identifiant, nécessite le mode développeur Discord activé) dans
   `DISCORD_GUILD_ID` — permet aux commandes slash de se synchroniser
   instantanément pendant les tests, au lieu d'attendre jusqu'à 1h pour
   une synchronisation globale.
4. `BACKEND_API_URL` pointe vers le backend FastAPI (par défaut
   `http://localhost:8000`, donc le backend doit tourner en parallèle).

## Lancer le bot

```bash
.venv/Scripts/python -m bot.main
```

## Tests

Seule la couche `bot/api_client.py` (appels HTTP vers le backend) est
testée unitairement, sans dépendre de Discord :

```bash
.venv/Scripts/python -m pytest
```

Le reste (`bot/cogs/session_flow.py`, `bot/main.py`) nécessite une vraie
connexion Discord pour être validé — pas encore testé en conditions
réelles.

## Limitation connue

Les boutons de confirmation envoyés en MP (`AssignmentActionView`) ne
survivent pas à un redémarrage du process du bot : l'identifiant de
l'assignment est capturé dans une closure Python, pas dans un
gestionnaire persistant basé sur `custom_id`. Si le bot doit tourner en
continu sur la durée, il faudra ajouter un registre de vues persistantes
(`bot.add_view(...)` au démarrage, dispatch par `custom_id`).
