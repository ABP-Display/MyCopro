# Prendre en main Copro.

## Installer votre immeuble

Connectez-vous avec le compte principal. Dans Administration, indiquez le nom de l’immeuble et son adresse. Dans Gestion immeuble, créez chaque copropriétaire avec son courriel et un mot de passe initial d’au moins 12 caractères. Le courriel devient son identifiant ; communiquez le mot de passe de façon adaptée et invitez la personne à le changer dans Mon compte.

Chaque copropriétaire a accès aux pages partagées en lecture : personnes et lots, comptes, charges, paiements, publications et outils. Les données financières de tous sont donc partagées dans ce périmètre, conformément au fonctionnement demandé. Les identifiants de session et mots de passe ne sont jamais listés. L’administration et les actions de modification exigent un rôle administrateur côté serveur.

Créez les lots avec leurs tantièmes et leur propriétaire. Un changement de propriétaire est historisé ; les anciens appels et paiements restent attribués à leur propriétaire d’origine. La nouvelle base n’effectue pas de régularisation juridique automatique à la vente.

## Comptes et charges

Dans Suivi des comptes, ajoutez un compte avec un nom, son titulaire, sa banque et son IBAN/BIC. Le solde de départ correspond au montant connu à la date choisie. Il devient immuable : n’ajoutez ensuite que les nouveaux mouvements, sans réenregistrer ceux déjà compris dans ce montant.

Pour une facture commune, choisissez Enregistrer une entrée / sortie, la banque débitée, le montant, la date et la référence. Vous pouvez lier une pièce jointe récente, préalablement publiée dans le fil. Une autre recette est possible ; les règlements des copropriétaires doivent passer par Paiements pour alimenter leur historique personnel.

Pour appeler un budget, ouvrez Charges courantes, saisissez le montant total voté, la référence de décision, la première échéance et le nombre d’appels. Par exemple : 12 000 €, 4 appels espacés de 3 mois. Le logiciel répartit le total entre les échéances, puis entre les lots selon les tantièmes. Vérifiez l’aperçu avant confirmation. Le total des parts est conservé au centime. Les dates et le type d’appel doivent correspondre à la décision de l’AG. Les appels ne sont pas automatiquement renouvelés d’une année à l’autre.

Travaux & exceptionnel fonctionne de la même façon avec un type de fonds ou d’appel distinct. Ce classement n’effectue pas le contrôle réglementaire des minima, plafonds ou clés spéciales de fonds travaux. Dans cette base simple, les répartitions utilisent les tantièmes généraux des lots.

## Vérifier les paiements

Enregistrez le copropriétaire qui a payé, la banque créditée, le montant réel et sa date. Sélectionnez si possible l’appel et le lot concernés. Si le paiement n’a pas encore été vérifié sur le relevé, laissez la case de vérification décochée.

La ligne apparaît À vérifier. Après contrôle sur la banque, Valider crée une seule entrée bancaire et met à jour la part payée. Écarter une ligne en attente la conserve sans mouvement bancaire. Une ligne déjà validée ne peut être validée une seconde fois. Pour un virement couvrant plusieurs appels, saisissez des parts distinctes dont la somme est exactement le versement reçu, avec une référence commune ; ne saisissez pas à nouveau le montant global.

Les versements sans appel restent identifiés comme non affectés. Ils figurent dans les encaissements du copropriétaire, sans solder artificiellement un appel précis. La base simple ne propose pas encore leur affectation ultérieure, l’annulation d’un paiement validé ou le rapprochement bancaire automatique. Vérifiez les lignes avant validation.

Choisissez une année et, si besoin, une personne pour retrouver les anciens versements. Les données ne sont pas effacées au changement d’année. L’écart annuel n’est pas un solde de clôture : il peut inclure des paiements d’une autre période ou des appels non encore exigibles. Le profil d’accueil affiche les versements personnels de l’année et les appels non soldés.

## Le fil commun

Un administrateur publie un texte avec une catégorie, éventuellement à la une et accompagné de documents. Tous les copropriétaires connectés peuvent lire et télécharger les pièces. La recherche porte sur le titre et le texte ; le filtre par catégorie conserve aussi les anciennes catégories désactivées. Les nouvelles publications utilisent seulement les catégories actives.

Le bouton Modifier la publication permet de corriger le titre, le texte ou la catégorie et d’ajouter des documents. Les pièces précédentes sont conservées ; elles ne sont pas supprimées par une correction du texte.

Les administrateurs personnalisent les catégories dans Administration : Travaux, Assurance, Trésorerie, ou tout autre sujet utile. Huit pièces jointes de 10 Mo maximum sont acceptées par publication ; la limite totale d’une requête est 12 Mo. Les téléchargements restent protégés par la connexion. Il n’y a pas d’envoi d’e-mail ni de modification collaborative des pièces.

## Outils et téléphone

Les outils sont accessibles à tous : ils calculent sans enregistrer d’opération. La liste des copropriétaires peut préremplir les calculs. Le simulateur de majorité ne remplace ni le choix de la majorité applicable ni le procès-verbal d’une AG.

Sur téléphone, utilisez le bouton de menu en haut. La version en bas de page propose de recharger l’application. L’installation PWA exige HTTPS (sauf localhost). Les fonctions privées nécessitent une connexion au serveur. L’affichage est contrôlé dans des navigateurs à plusieurs largeurs ; les comportements propres à Safari et à un téléphone réel restent à vérifier sur votre appareil.
