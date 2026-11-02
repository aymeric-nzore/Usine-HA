 # Usine HA

Cockpit de gestion d'usine construit avec Django, templates, HTMX et Tailwind CSS.

## Démarrage avec uv

Le projet conserve Python `>=3.11` comme compatibilité minimale et utilise Python
3.12 par défaut, notamment pour les builds Vercel.

```powershell
uv sync
Copy-Item .env.example .env
docker compose up -d postgres
uv run python manage.py migrate
uv run python manage.py seed_demo
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Le cockpit est disponible sur `http://127.0.0.1:8000/` et l'administration sur
`http://127.0.0.1:8000/admin/`.

Le seed crée quatre comptes de démonstration ivoiriens. Ils utilisent tous le mot de
passe `UsineHA2026!` en développement uniquement :

| Identifiant | Nom | Rôle |
|---|---|---|
| `amadou.dosso` | Amadou Dosso | Administrateur |
| `awa.kone` | Awa Koné | Responsable d'atelier |
| `yannick.kouadio` | Yannick Kouadio | Responsable d'équipe |
| `mariama.coulibaly` | Mariama Coulibaly | Opératrice terrain |

Le compte `amadou.dosso` est réservé à l’administration Django et ne peut pas ouvrir
une session sur `/connexion/`. Utiliser `/admin/` pour ce compte. Les autres comptes
accèdent au cockpit métier et aux écrans opérationnels selon leurs permissions.

Les écrans `/incidents/`, `/pieces/` et `/maintenance/` proposent la consultation,
création, modification et suppression protégées par les permissions Django.
Les formulaires de déclaration d’incident, de gestion de pièces et de planification
de maintenance sont validés par Django avant enregistrement.

Les menus, indicateurs, boutons et écrans sont filtrés selon le rôle :
responsable d’atelier (ateliers et production), collaborateur responsable
(équipes, lots et incidents). Le collaborateur responsable hérite aussi des
droits de consultation et d’action de l’opérateur (machines, incidents,
maintenance et pièces), en plus de ses propres écrans d’équipe.
Les mêmes permissions sont contrôlées côté serveur ; masquer un lien ne permet
donc pas de contourner les droits.

## Sélection et périmètre d’atelier

Après la connexion, chaque acteur choisit un atelier parmi ceux auxquels il est
rattaché : responsable direct de l’atelier, responsable d’équipe ou opérateur d’une
équipe. Le choix est conservé dans la session et toutes les listes, formulaires et
indicateurs sont filtrés sur cet atelier. Une tentative d’accès à un autre atelier
ne retourne aucune donnée.

Dans l’administration Django, un atelier possède un numéro, un libellé et un
responsable choisi parmi les utilisateurs acteurs. Les équipes et les pièces sont
également rattachées à un atelier.

La création d’un utilisateur dans l’administration demande son rôle et son atelier
d’appartenance. Pour un opérateur, l’équipe est obligatoire et un enregistrement
opérateur est créé automatiquement. Un collaborateur responsable peut être créé
sans équipe afin de résoudre la dépendance de création ; il pourra ensuite être
sélectionné comme chef d’équipe. Une équipe ne peut avoir qu’un seul responsable.
Un opérateur existant peut être promu depuis sa fiche utilisateur en lui attribuant
ce rôle, puis son équipe devient son équipe dirigée.

Les icônes utilisent Font Awesome. Le bloc `lottie-slot` dans `templates/base.html`
est prêt à recevoir une animation LottieFiles fournie par le client.

## Base PostgreSQL

Le développement utilise PostgreSQL via `compose.yml`. Après avoir copié
`.env.example` vers `.env`, le projet utilise la base `usine_ha` du conteneur
`usine-ha-postgres`.

Commandes utiles :

```powershell
docker compose up -d postgres
docker compose ps
uv run python manage.py migrate
uv run python manage.py seed_demo
docker compose logs -f postgres
docker compose down
```

Pour visualiser la base, utiliser **DBeaver** (application gratuite et complète)
ou **pgAdmin 4**. Dans VS Code, l’extension **SQLTools** avec
**SQLTools PostgreSQL/Cockroach Driver** permet de parcourir les tables et
d’exécuter des requêtes. Connexion locale : hôte `127.0.0.1`, port `55432`,
base `usine_ha`, utilisateur `usine`, mot de passe `usine_dev_password`.

## Production

### Déploiement Vercel + Supabase

Importer le dépôt dans Vercel avec le framework **Other**. Le fichier
`vercel.json` configure la fonction Django et la collecte des fichiers statiques.
Dans les variables d’environnement Vercel, définir :

- `SECRET_KEY` : une clé longue et aléatoire ;
- `DEBUG=False` ;
- `ALLOWED_HOSTS=.vercel.app` (ajouter le domaine personnalisé si nécessaire) ;
- `DATABASE_URL` : l’URI PostgreSQL Supabase avec `sslmode=require` ;
- `CSRF_TRUSTED_ORIGINS=https://votre-domaine.vercel.app` ;
- `VERCEL_URL` : généralement fournie automatiquement par Vercel.

Depuis Supabase, récupérer l’URI dans **Project Settings > Database > Connection
string**. Pour Vercel, utiliser de préférence la connexion poolée **Supavisor**
(port `6543`) et ne jamais utiliser les identifiants locaux Docker.

Après le premier déploiement, exécuter les migrations depuis un environnement
disposant des variables Vercel/Supabase :

```powershell
uv run python manage.py migrate
uv run python manage.py seed_demo
```

Le fichier `.env.example` contient uniquement des identifiants de développement.