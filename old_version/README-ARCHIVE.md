# Ancienne version de Copro.

Ce dossier contient l’application complète avant la simplification : backend, frontend, scripts, documentation, vitrine et références. Le commit de départ est dans `ARCHIVED_COMMIT.txt`. Ne modifiez pas cette copie pour développer la nouvelle application.

Les anciens volumes Docker restent `copro_postgres_data` et `copro_document_data`. La nouvelle application utilise d’autres volumes. Aucune reprise de données n’a été appliquée à l’ancienne base.

Pour consulter l’ancienne version en parallèle, depuis la racine du dépôt :

```sh
docker compose --env-file .env -f old_version/compose.archive.yaml up -d --build --wait
```

Elle devient accessible uniquement sur le serveur à <http://localhost:8082>. Les identifiants et la double authentification de l’ancienne instance restent ceux de cette instance. Les conteneurs d’archive utilisent les volumes historiques : toute action de gestion dans cette version modifierait donc ses données. Pour simplement l’arrêter, utiliser la même commande avec `stop` à la place de `up ...` ; ne pas supprimer ses volumes.

Le fichier `compose.yaml` d’origine reste inchangé dans ce dossier. Les scripts historiques sont conservés comme référence et nécessitent leur contexte d’origine ; ils ne sont pas ceux de la nouvelle base.
