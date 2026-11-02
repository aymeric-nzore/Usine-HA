# Usine HA — suivi des tâches

## Direction produit

Créer un cockpit d'exploitation industriel sobre et lisible : fond ivoire, bleu pétrole
pour la structure, jaune signal pour les alertes, sans dégradés. L'interface doit rester
utile sur tablette pour les équipes terrain.

## Tâches

- [x] Initialiser le projet Django avec `uv` et SQLite de développement.
- [x] Configurer les applications métier et les réglages statiques.
- [x] Modéliser les ateliers, lignes, produits, lots, incidents, machines, maintenances,
  pièces, fournisseurs et achats.
- [x] Ajouter les migrations, l'administration et les données de démonstration.
- [x] Construire le tableau de bord responsive avec navigation métier.
- [x] Ajouter les interactions HTMX pour filtrer les alertes sans rechargement complet.
- [x] Ajouter Font Awesome et un emplacement Lottie pour les états vides/chargement.
- [x] Ajouter les formulaires CRUD dédiés aux rôles opérationnels.
- [x] Ajouter les permissions par groupes et les utilisateurs de démonstration ivoiriens.
- [x] Filtrer les menus, indicateurs et actions selon les permissions du rôle.
- [x] Afficher et modifier les rôles utilisateurs depuis l’administration Django.
- [x] Faire hériter au collaborateur responsable les droits de base opérateur.
- [x] Ajouter la sélection d’atelier à la connexion et isoler les données par atelier.
- [x] Rattacher chaque atelier à un responsable acteur modifiable depuis l’admin.
- [x] Rattacher équipes et pièces à un atelier.
- [x] Vérifier les formulaires incident, stock et maintenance.
- [x] Ajouter la maintenance opérationnelle et le menu hamburger mobile.
- [x] Ajouter les écrans de connexion et déconnexion personnalisés.
- [x] Ajouter PostgreSQL avec Docker Compose, psycopg, migrations et seed.
- [x] Compléter les tests métier et les tests des parcours d’authentification/CRUD.

## Vérification

- `uv run python manage.py check`
- `uv run python manage.py makemigrations --check --dry-run`
- `uv run python manage.py migrate`
- `uv run python manage.py seed_demo`
- `uv run python manage.py test core` — 19 tests réussis.
- Parcours Playwright mobile validé : connexion, sélection d’atelier, maintenance et déconnexion vers `/connexion/` sans `next`.
- Formulaire de connexion validé : sélecteur d’atelier visible, ateliers actifs proposés,
  contrôle d’appartenance côté serveur et exemple d’identifiant `awa.kone`.
- Profil utilisateur validé : chaque utilisateur métier appartient à un atelier précis,
  modifiable dans sa fiche admin ; les comptes staff/admin restent exemptés.

## Dernière correction

- Le formulaire de création de pièce initialise désormais l’atelier sur son instance
  avant la validation Django, afin que la règle métier « une pièce doit être rattachée
  à un atelier » soit compatible avec `ModelForm.is_valid()`.
- La connexion opérationnelle demande désormais directement l’atelier, initialise la
  session avec ce choix et redirige vers le tableau de bord ou la destination sûre.
- Le modèle `UserProfile` porte l’appartenance directe `utilisateur → atelier` (un
  utilisateur ne possède pas un atelier) et son inline d’administration est visible
  depuis `/admin/auth/user/`.
- Les pages « Ateliers & lignes » et « Production » sont disponibles via des routes
  dédiées, filtrées sur l’atelier d’appartenance de l’utilisateur et protégées par
  leurs permissions Django.
- PostgreSQL est lancé par `compose.yml` dans `usine-ha-postgres`. Le port hôte est
  `55432` pour éviter un conflit local sur `5432`; Django utilise `DATABASE_URL` depuis
  `.env`. Les migrations et le seed ont été exécutés sur cette base.
- La création d’utilisateur dans l’administration fonctionne avec le formulaire Django
  natif ; la personnalisation du champ de rôle est conditionnée à sa présence et
  l’atelier est proposé via l’inline `UserProfile`.
- Le responsive du cockpit couvre désormais les écrans mobiles et tablettes : le menu
  hamburger ouvre la navigation latérale, les tableaux restent consultables par
  défilement horizontal et les formulaires évitent le zoom automatique sur iOS.
- La préparation Vercel/Supabase est validée : `api/index.py`, `vercel.json`,
  WhiteNoise, collecte statique, hôtes Vercel et origines CSRF sont configurés.
  Les variables `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`,
  `CSRF_TRUSTED_ORIGINS` et `VERCEL_URL` restent à renseigner dans Vercel.
- La création admin d’un utilisateur demande désormais le rôle et l’atelier
  d’appartenance. L’équipe est obligatoire pour les opérateurs mais facultative pour
  un collaborateur responsable, afin d’éviter la boucle de création. Le profil
  existant est réutilisé pour éviter une insertion `UserProfile` en double.
- Une équipe doit sélectionner un utilisateur ayant le rôle « Collaborateurs
  responsables » comme chef d’équipe. Un lien est proposé dans l’admin pour créer
  rapidement ce collaborateur. La promotion d’un opérateur conserve son équipe et
  lui attribue la responsabilité si elle est encore disponible ; une contrainte
  d’unicité empêche une personne de diriger plusieurs équipes.
