# Charges, paiements et historique des lots

Le parcours conserve le thème actuel et les règles du moteur comptable. Il distingue **les personnes qui paient**, **les lots permanents** et **les appels de charges**.

## 1. Renseigner le RIB

Dans **Charges & finances → Demander des charges → RIB de la copropriété**, renseigner le titulaire, l’IBAN et, si disponible, le BIC. Ces coordonnées servent aux avis individuels. Un IBAN doit être renseigné avant de préparer les nouveaux appels guidés et leurs PDF.

Les comptes sont aussi accessibles directement dans **Gestion comptable → Comptes bancaires**. Créer une fiche par compte bancaire avec un code comptable 512 distinct (proposé automatiquement), un nom explicite, l’établissement, le titulaire et le RIB. Un compte comptable déjà utilisé peut être associé à sa banque sans déplacer ni recréer ses mouvements. Le compte par défaut sera proposé lors des règlements, tout en restant modifiable.

**Voir les entrées et sorties** affiche une période au choix, le solde avant la période, les entrées, les sorties et le solde final. Les paiements identifiés indiquent la personne et les appels/lots explicitement affectés ; les règlements de factures conservent le fournisseur et le lien vers la pièce jointe. Les anciens mouvements non identifiés restent visibles avec leurs comptes de contrepartie. Les transferts entre comptes sont également conservés. Les reports de clôture ne comptent pas deux fois l’argent déjà présent dans l’historique.

Pour reprendre des soldes bancaires existants lors du démarrage, utiliser **Renseigner les soldes de départ** : cette action ouvre la reprise comptable, qui doit comprendre les contreparties nécessaires pour équilibrer l’ensemble des soldes. Ne pas enregistrer un faux paiement de copropriétaire pour obtenir un solde bancaire. Un solde calculé ne remplace pas le contrôle avec les relevés de banque.

## 2. Partir du montant voté

Cliquer sur **Créer des appels de charges**. Choisir un budget dont la décision a été enregistrée après signature du PV dans l’application, ou saisir la référence d’une AG réalisée à l’extérieur. Les budgets numériques proposent leur montant restant à appeler pour la répartition concernée : les appels déjà existants du même exercice sont pris en compte pour éviter de les appeler deux fois.

Pour un appel exceptionnel de travaux, choisir les travaux votés et leur clé. Les appels déjà préparés depuis la décision sont pris en compte. Fonds travaux et avances conservent leurs contrôles spécialisés ; il ne suffit pas de choisir un intitulé pour contourner les décisions et plafonds applicables.

L’assistant comporte trois étapes : décision et répartition, montant et échéances, puis aperçu lot par lot. Les propriétaires sont recherchés à la date d’exigibilité. Une modification entre aperçu et confirmation impose une nouvelle vérification.

**Exemple :** 12 000 € de budget annuel, quatre échéances trimestrielles et 1 000 tantièmes. Le lot de 120 tantièmes reçoit 1 440 € par an, soit 360 € par trimestre. Un appel exceptionnel de 3 000 € sur la même répartition donne 360 € pour ce lot. Les arrondis conservent le total au centime.

Les dates et la périodicité doivent correspondre à la décision votée. Les dates futures restent en préparation ; elles ne sont pas comptabilisées à l’avance. Utiliser la validation à la date autorisée pour publier l’appel.

## 3. Préparer les avis PDF et les courriels

Sur un appel validé, ouvrir **Avis PDF et courriels**, puis **Préparer les avis PDF individuels**. Un avis regroupe les lots de chaque propriétaire, ses tantièmes, son montant, l’échéance, la référence du virement et le RIB de la copropriété.

Les éditions sont conservées comme pièces privées avec une empreinte et un instantané des données utilisées. Changer le RIB plus tard ne réécrit pas les anciens PDF. Répéter la préparation avec les mêmes données ne duplique pas les avis. Les documents nominatifs ne peuvent pas être partagés globalement depuis la bibliothèque.

**Préparer le courriel** ouvre votre messagerie avec le destinataire, le montant et la référence. **Télécharger le PDF puis le joindre au message** : un lien `mailto` ne joint pas automatiquement le fichier. Aucun e-mail n’est envoyé automatiquement par ce parcours, conformément au choix de messagerie préparée.

L’avis décrit la somme appelée ; les versements déjà effectués doivent être vérifiés sur le compte avant de payer à nouveau. Il n’est pas une relance d’impayé.

## 4. Enregistrer puis rattacher le paiement

Dans **Paiements des copropriétaires**, cliquer sur **J’ai reçu un paiement**. Choisir la personne, l’exercice de l’écriture, le montant réellement reçu, la date et la banque créditée. Sélectionner l’appel et le lot concernés, et préciser la part du versement à rattacher. Un paiement partiel est possible.

**Exemple :** une personne règle 500 € en un seul virement pour deux lots. Enregistrer une seule fois 500 €, puis rattacher 360 € au premier appel/lot. Le reste, 140 €, demeure sur son compte ; utiliser **Voir ses paiements → Rattacher à un appel / lot** pour le second lot. Ne pas enregistrer un deuxième encaissement de 140 €.

Un paiement peut aussi rester en avance, à affecter ensuite. Un versement ancien sans lot identifié demeure conservé sur la personne ; le logiciel n’invente pas son attribution au propriétaire actuel. Les rapprochements historiques déjà existants peuvent recevoir une précision de lot, sans réenregistrer d’argent ni annuler les écritures.

Le rattachement passe par les contrôles existants de rapprochement. Il ne peut pas attribuer le paiement d’une personne à la dette d’une autre, ni affecter plus que le montant disponible. Les annulations et délettrages restent tracés par le moteur comptable ; ils ne détruisent pas les reçus originaux.

## 5. Lire une année ou retrouver les anciennes

Le gestionnaire choisit une **année civile** pour voir les paiements par personne, puis ouvre le détail. Le solde affiché à côté reste le solde actuel ; il ne prétend pas être le solde de clôture de cette année.

Dans son espace, le copropriétaire retrouve **Mes charges et mes paiements** : montant payé dans l’année sélectionnée, solde actuel, paiements enregistrés depuis l’origine, détail de chaque versement et avis PDF personnels. Le relevé annuel PDF et l’historique comptable détaillé restent disponibles, y compris pour les années précédentes.

Les montants payés additionnent les encaissements réels enregistrés, hors paiements annulés. Une régularisation, un report ou une correction au crédit ne constitue pas à lui seul un nouveau paiement. Si les anciens versements n’ont pas été repris comme encaissements dans l’application, une simple balance d’ouverture ne permet pas de reconstituer leur montant : conserver/importer les justificatifs correspondants.

Les écritures et rattachements sont enregistrés durablement, sans remise à zéro au changement d’année. Cette conservation dans la base ne remplace pas les [sauvegardes chiffrées base et documents](SAUVEGARDE-SECURITE.md), leur programmation et leur copie hors serveur.

## 6. Un lot reste, son propriétaire peut changer

Dans la liste des lots, **Historique et vente** affiche les propriétaires successifs, les appels initiaux et les paiements explicitement rattachés. Pour une vente, choisir le nouveau propriétaire, la date d’effet et la référence de notification. Examiner les ajustements proposés avant confirmation.

Les paiements déjà versés restent au nom de la personne qui les a effectués. Les appels et leurs répartitions d’origine ne sont pas réécrits ; les ajustements nécessaires sont enregistrés séparément. Un lot ayant un historique ne peut pas changer simplement de propriétaire en modifiant sa fiche.

Une ancienne dette ne doit pas devenir automatiquement une dette du nouvel arrivant. Les règles d’exigibilité et de régularisation, ainsi que les accords privés entre vendeur et acquéreur, demandent de conserver les dates et justificatifs. [Service Public — charges l’année de la vente](https://www.service-public.gouv.fr/particuliers/vosdroits/F32920), [décret du 17 mars 1967, article 6-2](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000053191265/2026-05-26).

L’historique complet d’un lot est réservé au gestionnaire ; le copropriétaire ne reçoit pas les coordonnées ou paiements des autres occupants successifs. L’ancien propriétaire conserve l’accès à son propre compte, selon les règles d’accès existantes.
