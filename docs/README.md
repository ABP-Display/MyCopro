# Vitrine de Copro.

`index.html` est un site statique de présentation du projet. Les styles, le script de navigation et le logo se trouvent dans `assets/`. Le guide de l’application reste dans [UTILISATION.md](UTILISATION.md).

## Consulter

Ouvrir directement `index.html` dans un navigateur. Aucun serveur, package JavaScript, accès à la base ou compilation n’est nécessaire. Les boutons d’accès ouvrent **https://copro.ydoxide.fr**. Les visuels d’interface utilisent des données fictives et aucun compte réel.

## Publier avec GitHub Pages

Après avoir poussé ces fichiers dans le dépôt, ouvrir **Settings → Pages**, choisir **Deploy from a branch**, sélectionner la branche contenant les fichiers et le dossier **/docs**, puis enregistrer. `.nojekyll` conserve la publication statique. Si la source est actuellement GitHub Actions, la remplacer par cette publication depuis une branche pour utiliser ce mode.

Le site utilise des liens relatifs pour ses ressources : il fonctionne aussi sous le sous-chemin d’un dépôt GitHub Pages. Il ne contient pas de domaine personnalisé imposé, de bibliothèque externe, de police distante ni de traceur. Aucun déploiement GitHub n’est effectué par la création de ces fichiers.

Référence : [configuration de la source GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).
