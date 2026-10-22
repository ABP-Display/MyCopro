# Les six priorités de gestion quotidienne

Point du **20 octobre 2026**, pour un syndic bénévole ou coopératif. Les parcours
ci-dessous sont disponibles dans l’instance locale. Les limites du cahier complet
restent suivies dans l’[audit](AUDIT-FONCTIONNALITES.md).

| Besoin | Où l’utiliser | Ce qui est disponible |
| --- | --- | --- |
| Gestion des copropriétaires | Copropriétaires ; Lots & tantièmes | Fiches, courriels, lots, tantièmes regroupés, accès et changement du mot de passe temporaire. |
| Intranet et relevé personnel | Connexion avec un compte copropriétaire | Solde actuel, historique paginé, filtre de dates, soldes initial/final de période, PDF et CSV du relevé ; documents et annonces publiés. |
| Documents d’AG et comptables | Assemblées générales ; Rapports comptables ; Documents | Dossier AG, pièces, votes, PV, cinq annexes, bibliothèque versionnée, partage explicite et contrôle de relecture des éditions officielles. |
| Factures communes | Charges & finances → Dépenses | Facture d’eau, d’électricité, d’assurance ou autre, fournisseur, pièce, compte de charge, clé de répartition, règlements partiels et suivi comptable. |
| Calcul et traitement | Outils | Majorités, répartition annuelle avec équivalents mensuels/trimestriels, chargement de l’annuaire et échéancier au centime. Ces simulations ne créent aucune écriture. |
| Modèles à compléter | Documents → Modèles à remplir | Information, demande de devis, demande d’intervention et point amiable sur un solde débiteur ; destinataire repris de l’annuaire, contenu éditable, aperçu et PDF privé. |

## Consulter son relevé

1. Ouvrir l’application avec son courriel copropriétaire et son mot de passe.
   Un accès nouvellement créé impose de changer le mot de passe temporaire.
2. Dans **Mon compte copropriétaire**, lire le solde actuel. Positif : compte
   débiteur ; négatif : compte créditeur. Un solde seul ne prouve pas un retard.
3. Choisir **Du / Au**, puis **Afficher la période**. Les totaux portent sur toute
   cette période ; le solde actuel reste distinct du solde à la date de fin choisie.
4. Utiliser **Précédent / Suivant** pour parcourir les mouvements, par pages de 50,
   sans la limite antérieure des 100 derniers mouvements.
5. Télécharger **mon relevé PDF** ou **les mouvements CSV** : l’export porte sur
   toute la période appliquée, pas sur la page affichée. Au-delà de 10 000 mouvements,
   réduire la période ; aucune troncature silencieuse n’est réalisée.

Le serveur déduit le propriétaire depuis la session : changer un paramètre d’URL
ne permet pas d’accéder au relevé d’une autre personne. L’ancien propriétaire
conserve le seul compte individuel selon les règles d’accès existantes.

## Préparer un modèle de document

1. En gestion, ouvrir **Documents → Modèles à remplir**.
2. Choisir le modèle, puis éventuellement un copropriétaire ou un fournisseur.
   Le nom, le courriel disponible, les coordonnées du fournisseur et la signature
   proposée sont préremplis. L’adresse postale du copropriétaire n’est pas inventée.
3. Compléter le titre, la date, le destinataire, l’objet et le texte. Remplacer
   toutes les mentions **[À compléter]**. L’aperçu suit la saisie.
4. Relire puis cocher la confirmation et **Créer le PDF privé**.
5. Télécharger le PDF ou le retrouver dans **Bibliothèque → Courriers préparés**.
   Il possède une version et une empreinte comme les autres documents. Son partage
   ultérieur est une action distincte ; les anciens fichiers restent conservés.

Changer de modèle ou de destinataire recharge le texte proposé. L’éditeur ne
conserve pas de brouillon textuel après avoir quitté la page : le PDF créé, lui,
reste dans la bibliothèque. Pour conserver une correction après création, préparer
un nouveau document ou ajouter une version dans la bibliothèque.

Le modèle de point amiable exige un copropriétaire présentant un solde débiteur
actuel. Ce courrier n’est pas une mise en demeure ; il n’affirme pas qu’un paiement
est en retard. Aucun modèle ne signe, n’envoie ni ne crée d’opération comptable.

## Documents AG et comptables

La bibliothèque de courriers ne remplace pas les documents calculés d’une AG ou
d’un exercice. Convocations, pouvoirs, correspondance, présence, PV et annexes
restent produits par leurs parcours : ils reprennent le dossier figé, ses votes,
ses versions de pièces et ses comptes. Les contrôles de validation métier
continuent de s’appliquer aux éditions officielles.

Voir les guides [AG](AG-PREMIERS-PAS.md), [comptabilité](COMPTABILITE-CYCLE.md) et
[validation des documents](VALIDATION-DOCUMENTS.md).

## Ce qui reste à compléter

Les modèles juridiques spécifiques (mise en demeure, attestations réglementaires),
la signature et les envois connectés ne sont pas couverts par ces courriers simples.
L’intranet ne dispose pas encore de messagerie, tickets d’incident ou paiement en ligne.
Les compteurs individuels et imports de consommations d’eau/chauffage restent à
créer : une facture commune peut déjà être répartie selon les clés existantes.

Validation technique : **255 tests PostgreSQL réussis**, dont onze nouveaux tests
des modèles et relevés ; compilation TypeScript/Vite, contrôles des PDF longs,
aperçu/confirmation, filtres/pagination et écrans à 1 440 et 390 px. Les essais
d’interface utilisent des données simulées et ne créent pas de courriers dans
l’instance. Aucune nouvelle validation métier réelle des modèles AG n’est déclarée.
