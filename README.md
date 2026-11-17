# Copro. — une base simple pour votre immeuble

Une application pour un syndic bénévole ou coopératif, en React, Django et PostgreSQL. Le design Copro. est conservé : couleurs vertes, logo, texte courant de 14 px, menu compact et affichage mobile.

## Quatre rubriques

- **Gestion immeuble** : copropriétaires avec accès personnel, lots, tantièmes et historique des changements de propriétaire.
- **Gestion financière** : comptes bancaires et RIB, soldes de départ, entrées/sorties, charges courantes, fonds travaux et appels exceptionnels répartis par tantièmes, aperçu d’échéancier, paiements à vérifier puis valider, historique par année.
- **Vie de la copropriété** : fil de publications avec texte, pièces jointes, recherche, catégories personnalisables et informations à la une.
- **Outils** : répartition annuelle/mensuelle/trimestrielle, simulation d’échéances et calcul de majorité avec liste des copropriétaires ou saisie libre. Les simulations ne créent aucune opération.

Les copropriétaires consultent toutes ces rubriques et utilisent les simulateurs. Les écritures, publications, modifications et validations sont réservées aux administrateurs, avec contrôle côté serveur. **Administration** n’apparaît que pour eux : coordonnées, catégories, rôles et historique. Chacun peut modifier son propre mot de passe.

## Démarrer

1. Copier `.env.example` vers `.env` et renseigner des secrets robustes. Le mot de passe administrateur doit contenir au moins 12 caractères.
2. Lancer `docker compose up -d --build --wait`.
3. Ouvrir <http://localhost:8081>. Le compte principal utilise `ADMIN_USERNAME` et `ADMIN_PASSWORD` du fichier `.env`.
4. Renseigner l’immeuble, créer les copropriétaires et leurs accès, affecter les lots, puis ajouter les comptes bancaires.

Voir le [guide quotidien](docs/UTILISATION.md). La PWA reste disponible sous HTTPS ou sur localhost. Les fichiers privés et les réponses API ne sont pas conservés dans le cache hors connexion. La version `AAAA.MM.JJ.HHMM` en bas de page permet de demander un rechargement.

## Ancienne version et données

L’application précédente, sa documentation et ses références sont conservées dans [`old_version/`](old_version/README-ARCHIVE.md), avec le commit source indiqué dans `ARCHIVED_COMMIT.txt`.

**La nouvelle version démarre vide dans des volumes distincts** : `copro_simple_postgres_data` et `copro_simple_document_data`. Les anciens volumes `copro_postgres_data` et `copro_document_data` ne sont ni effacés ni convertis. Il n’y a pas de reprise automatique de l’ancienne comptabilité. Avant la bascule locale, une sauvegarde chiffrée de l’ancienne version a été contrôlée par restauration ; ses fichiers et sa clé sont privés, hors Git, dans `.local-data/`.

Ne lancez pas `docker compose down -v` pour une simple mise à jour. Les sauvegardes de la nouvelle base et des documents se créent avec `python scripts/backup.py` ; elles contiennent des données personnelles, ne sont pas chiffrées et doivent être stockées dans un emplacement privé. Ce script crée une copie cohérente ; il ne remplace pas une restauration de contrôle.

## Portée de cette nouvelle base

Il s’agit d’un **suivi de trésorerie simple**, et non de toute l’ancienne comptabilité réglementaire. Les annexes réglementaires, la gestion complète des AG, la double authentification, les avis PDF automatiques et l’ancien système de restauration vérifiée restent dans l’archive ; ils ne sont pas annoncés comme disponibles dans cette nouvelle base. Les décisions et règles de répartition doivent être vérifiées avant création des appels. Les montants versés et les sommes appelées sont conservés séparément, sans considérer un appel comme de l’argent encaissé.

## Développement et vérifications

```sh
docker compose run --rm backend python manage.py test copro --noinput
docker compose run --rm backend python manage.py makemigrations --check --dry-run
docker compose build frontend
```

Code actif : `backend/copro/` pour les données et API, `frontend/src/` pour l’interface. Les éléments visuels et les calculateurs éprouvés ont été réutilisés de l’ancienne application ; les écrans et le modèle de données ont été simplifiés. Les calculateurs restent des aides à la préparation, avec leurs sources officielles accessibles depuis l’outil.
