# Essayer la vie d’une copropriété fictive

Jeu de données DÉMO arrêté au **15 octobre 2026**. Les noms, courriels `.test`,
factures, paiements, preuves et signatures sont fictifs. Aucun message ni ordre
bancaire n’est envoyé. Les données qui existaient avant la simulation sont conservées.

## Les cinq profils à essayer

| Personne fictive | Paiements courants 2026 | Travaux et fonds | Solde attendu au 15/10/2026 |
| --- | --- | --- | --- |
| Alice Martin | 300 € par mois, janvier à octobre | Réglés | 300 € débiteurs |
| Bruno Petit | 750 € chaque trimestre | Réglés | 250 € créditeurs |
| Chloé Bernard | 2 400 € versés en avance, en janvier | Réglés | 200 € créditeurs |
| David Leroy | 150 € versés seulement | Non réglés | 1 890 € débiteurs |
| Emma Roux | Aucun versement 2026 | Non réglés | 1 360 € débiteurs |

Ces soldes incluent les excédents de 2025 reportés : 300, 250, 200, 150 et 100 €
respectivement. **Débiteur** signifie restant dû au syndicat ; **créditeur** signifie
avance ou excédent au bénéfice du copropriétaire. Le vieillissement et le lettrage
permettent d’examiner les échéances : un solde seul ne suffit pas à établir un impayé.

Les provisions de charges courantes sont appelées par trimestre pour tous les lots.
Alice illustre des **versements mensuels** sur ces appels trimestriels ; les paiements
mensuels ne génèrent pas une deuxième dette. Un appel de fonds peut porter sur les
charges courantes, des travaux votés ou le fonds travaux : ces natures sont distinctes.

## Où cliquer

1. **Copropriétaires** : retrouver les cinq fiches dont le prénom commence par `[DÉMO]`.
   Leurs accès temporaires sont conservés dans le fichier privé indiqué lors de
   l’installation, pas dans ce guide ni dans le dépôt Git.
2. **Lots & tantièmes** : voir les cinq appartements `DEMO-A1` à `DEMO-A5` et le
   parking `DEMO-P3`. Chloé possède un appartement et le parking : son compte
   réunit ses deux lots. La clé **[DÉMO] Lots fictifs uniquement** totalise 1 000
   tantièmes et exclut les lots préexistants. Le total global de l’immeuble inclut
   aussi vos anciens lots ; il peut donc être supérieur à 1 000.
3. Choisir **l’exercice 2026** dans les écrans financiers. Si un exercice existait
   déjà, son nom est conservé, par exemple `test`.
4. **Charges & finances → Appels de fonds** : comparer les quatre provisions
   courantes de 3 000 €, l’appel travaux de 2 000 € et le fonds travaux de 600 €.
   Pour un nouvel essai, sélectionner la clé DÉMO, sans utiliser la clé générale
   préexistante qui englobe tous les lots.
5. **Gestion comptable → Encaissements / lettrage** : examiner les versements et
   leurs imputations ; les trois premiers profils ont payé leurs travaux et fonds.
6. **Rapports comptables → Comptes copropriétaires** : comparer avec le tableau
   ci-dessus, puis examiner le grand livre et les échéances.
7. **Banques** : le compte courant DÉMO affiche **4 050 €**, le compte du fonds
   travaux **450 €**. Trois relevés fictifs sont importés, rapprochés et validés :
   l’année 2025, puis les deux comptes jusqu’au 15 octobre 2026.
8. **Factures / comptes fournisseurs** : voir **1 800 €** restant à payer :
   900 € sur l’eau et 900 € sur l’électricité. Les factures de nettoyage,
   d’assurance et de portail sont réglées. Les PDF sont dans Documents.
9. **Fonds & travaux votés** : le portail a un budget/appel de 2 000 €,
   1 200 € réalisés et payés, et 800 € en attente. Le fonds travaux est distinct :
   600 € appelés, 450 € payés et placés sur son compte, 150 € non versés.
10. **Dossier comptable annuel** : examiner les concordances et décomptes ; 2025
    est clôturé avec 12 000 € de provisions, 11 000 € de charges et un excédent
    de 1 000 €. La régularisation 2026 reste une préparation, pas une approbation.

## Deux AG pour comprendre le parcours

Dans le sélecteur d’assemblée, choisir un dossier portant `[DÉMO]`.

**AG du 14 mars 2026 — simulation terminée** : cocher **Inclure les archives**.
Le dossier conserve les convocations, les présences, un formulaire de correspondance,
quatre votes, un opposant, un absent, le PV et la présence avec signatures simulées,
les notifications fictives et quatre mises en œuvre. Ces décisions ont alimenté la
régularisation 2025, le budget 2026, les appels restants et les travaux du portail.
La clôture 2025 et le report 2026 sont effectués par les services comptables.

**AG d’entraînement — à terminer** : les convocations fictives sont préparées,
mais la séance et les votes ne sont pas enregistrés. Dans **Présences & droits de
vote**, choisir les personnes présentes, représentées ou absentes. Les titulaires
des lots antérieurs sont conservés dans le corps électoral, absents dans le scénario
terminé ; ils n’ont reçu aucune charge DÉMO. Les résolutions utilisent la clé des
lots fictifs. Suivre ensuite le [guide AG](AG-PREMIERS-PAS.md) pour ouvrir la séance,
saisir les votes, préparer le PV et conserver ses pièces d’entraînement.

Les dates de l’AG historique et des preuves sont simulées dans le seul processus
d’import, sans modifier l’horloge du serveur. Une preuve simulée n’est pas une
notification réelle ; un PDF fictif n’est pas une signature. Aucun avis métier
réel ni validation officielle des modèles n’est créé par ce scénario.

## Essayer un accès copropriétaire

Ouvrir une fenêtre privée du navigateur, saisir un courriel fictif et son mot de
passe temporaire depuis le fichier privé des accès. Choisir un nouveau mot de
passe à la première connexion. L’espace affiche le **compte de la personne
connectée**, ses mouvements et les données partagées autorisées. Il ne donne pas
accès aux journaux privés, au dossier de gestion AG ni à la saisie d’écritures.

## Reproduire les tests sans modifier l’instance

```sh
docker compose exec backend python manage.py test core.test_demo --noinput
```

Ces tests recréent le scénario dans une **base de test séparée**, vérifient les
montants indépendamment, les droits, les pièces, l’AG, le refus d’un règlement
excessif ou futur, l’absence de duplication et le retour arrière en cas d’échec.
Ne pas lancer plusieurs suites simultanément sur la même base de test.

## Charger le scénario sur une nouvelle installation

Faire d’abord une sauvegarde complète base et documents. La commande refuse les
instances qui comportent déjà des écritures ou un paramétrage financier incompatible.
Elle conserve les contacts, lots, organisation et exercice 2026 existants. Elle
ajoute un profil de fonds travaux fictif de 600 € pour 2026 si aucun profil n’existe.

Sans `--apply`, la commande ne modifie rien :

```sh
docker compose exec backend python manage.py simulate_copro
```

Exemple d’import avec fichiers hôtes privés, à adapter au système :

```sh
mkdir -p .local-data/demo
docker compose run --rm --no-deps -T \
  -v "${PWD}/.local-data/demo:/demo-private" \
  backend python manage.py simulate_copro --apply --user admin --with-access \
  --access-file /demo-private/acces.md --report-file /demo-private/rapport.json
```

Sous PowerShell, écrire sur une ligne ou remplacer les `\` de continuation par
l’accent grave. Les mots de passe ne sont jamais affichés dans le journal ni mis
dans le README. Un second lancement ne duplique pas le scénario et ne réinitialise
aucun mot de passe. Les rapports recalculés après vos essais peuvent naturellement
différer des valeurs initiales.

Il n’existe pas de suppression globale automatique des données DÉMO : après vos
essais, décider des données à conserver avant une reprise réelle. Restaurer la
sauvegarde préalable remplacerait aussi les changements faits depuis sa création.
