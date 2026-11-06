# Installer Copro. et utiliser la version mobile

L’application de gestion est installable comme PWA, avec son logo, un raccourci et une fenêtre autonome. Le thème habituel reste conservé ; les formulaires, menus, tableaux et fenêtres s’adaptent aux petits écrans.

## Installation

Ouvrir l’adresse **HTTPS** de l’instance, par exemple `https://copro.ydoxide.fr/connexion`, puis :

- Chrome / Edge : utiliser l’option d’installation du navigateur. Le lien **Installer Copro.** en bas de page ouvre aussi l’aide et propose un bouton lorsque le navigateur autorise cette installation.
- iPhone / iPad : Safari → Partager → Sur l’écran d’accueil.
- Le lancement ouvre la connexion habituelle. Les règles de mot de passe et de double authentification restent identiques.

`http://localhost:8081` permet les essais sur le PC. L’adresse HTTP d’un autre appareil du réseau local ne constitue généralement pas un contexte sécurisé : utiliser le domaine HTTPS pour installer sur un téléphone. La proposition d’installation dépend aussi du navigateur et de son état, notamment si l’application est déjà installée.

## Version et rechargement

La version est calculée à la compilation avec l’heure **Europe/Paris**, au format `AAAA.MM.JJ.HHMM`. Elle identifie les fichiers affichés, pas une sauvegarde de la base. Une image Docker de compilation réutilisée garde son numéro existant.

Cliquer sur cette version en bas de page ouvre une confirmation. **Plus tard** conserve l’écran. **Recharger et mettre à jour** vérifie la connexion, récupère la version disponible, active le service worker en attente puis recharge la page. Les champs non enregistrés sont perdus ; cookies de connexion et données serveur ne sont pas effacés. Si le serveur est inaccessible, la fenêtre affiche l’erreur sans recharger.

Le déploiement doit publier l’image frontend à jour, pas seulement modifier les sources. Les fichiers HTML, `sw.js` et `version.json` sont servis sans cache durable ; les fichiers compilés dont le nom contient une empreinte restent immuables.

## Hors connexion et cache

Le service worker met en cache uniquement les ressources publiques de l’interface et la page de secours. Il ne met en cache **aucune réponse `/api/`**, aucun relevé, document privé, mot de passe ou secret de double authentification. Il n’existe pas de saisie ou synchronisation comptable hors connexion.

Quand une page est ouverte sans réseau après installation du worker, Copro. affiche une page demandant de se reconnecter. Les trois caches statiques les plus récents sont conservés pour faciliter les transitions de version ; les plus anciens sont supprimés à l’activation.

## Mon compte et ma sécurité

La fenêtre comporte un en-tête, deux vues **Double authentification** / **Mot de passe**, des formulaires encadrés et un pied de fenêtre. La navigation au clavier, la fermeture par Échap et les contrôles serveur existants sont conservés. Sur mobile, les champs sont agrandis sans modifier la taille habituelle du texte sur ordinateur.

## Vérifications réalisées

Sur une copie isolée des fichiers compilés et avec des API fictives : critères d’installation du navigateur, dimensions des icônes, activation d’une nouvelle version après confirmation, annulation, échec de mise à jour hors connexion sans rechargement, page de secours et absence d’API dans les caches. Fenêtres gestionnaire/copropriétaire vérifiées aux largeurs 320, 390, 768 et 1 440 px. La procédure iOS est documentée ; elle n’a pas été exécutée sur un appareil iOS réel.

Références techniques : [installation des PWA — MDN](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable), [cycle de vie des service workers — MDN](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers).
