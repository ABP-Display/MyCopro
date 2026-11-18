# Prendre en main Copro.

## Installer votre immeuble

Connectez-vous avec le compte principal. Dans Administration, indiquez le nom de l’immeuble et son adresse. Dans Gestion immeuble, créez chaque copropriétaire avec son courriel et un mot de passe initial d’au moins 12 caractères. Le courriel devient son identifiant ; communiquez le mot de passe de façon adaptée et invitez la personne à le changer dans Mon compte.

Chaque copropriétaire a accès aux pages partagées en lecture : personnes et lots, comptes, charges, paiements, publications et outils. Les données financières de tous sont donc partagées dans ce périmètre, conformément au fonctionnement demandé. Les identifiants de session et mots de passe ne sont jamais listés. L’administration et les actions de modification exigent un rôle administrateur côté serveur.

Les listes sont des cartes : le nom ou la référence se trouve en tête, les informations sont regroupées dessous et le bouton stylo ouvre la modification. Dans une carte copropriétaire, la flèche circulaire prépare une réinitialisation des accès. La fenêtre affiche le destinataire, un nouveau mot de passe généré et l’aperçu du message. Le mot de passe actuel n’est remplacé qu’en cliquant sur Confirmer et préparer le courriel.

Une fois la réinitialisation confirmée, Ouvrir le courriel dans ma messagerie prépare un message avec le lien de connexion, l’identifiant réel et le nouveau mot de passe. Vous devez envoyer le message depuis votre messagerie. Le mot de passe généré n’est pas conservé en clair dans l’historique de l’application et n’est plus affiché après fermeture de cette fenêtre. Les anciennes sessions du destinataire sont invalidées ; son A2F reste active. Votre propre mot de passe se modifie dans Mon compte. Un compte inactif doit d’abord être réactivé.

Configurez `COPRO_PUBLIC_URL` avec l’adresse accessible aux copropriétaires, par exemple `https://copro.ydoxide.fr`, puis recréez le service backend. Cette adresse sert au lien de connexion du courriel ; elle évite d’envoyer un lien localhost inutilisable depuis un autre appareil. Ne réinitialisez pas une seconde fois uniquement pour rouvrir le brouillon : conservez le courriel préparé avant de fermer la fenêtre.

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

## Mon compte, A2F et mises à jour

**Mon compte** permet de modifier le mot de passe en saisissant le mot de passe actuel, le nouveau et sa confirmation. Avec l’A2F activée, un code de l’application ou de secours est aussi demandé. Les autres sessions sont invalidées après un changement de mot de passe.

Pour activer l’A2F, confirmez votre mot de passe puis scannez le QR code dans Google Authenticator ou une application TOTP. Vous pouvez aussi saisir la clé affichée en choisissant le mode basé sur l’heure : six chiffres, renouvelés toutes les 30 secondes. La préparation est horodatée et expire après dix minutes. Saisissez le premier code pour confirmer : la protection ne s’active qu’après cette vérification. L’heure automatique doit être activée sur le téléphone et sur le serveur.

Huit codes de secours sont alors affichés une seule fois. Téléchargez-les et conservez-les en lieu sûr, séparément du téléphone. Chacun remplace un code de l’application pour une seule utilisation. Le code employé pour l’activation est déjà consommé : pour une action immédiate, attendez le code suivant ou utilisez un code de secours. La date d’activation et le nombre de codes de secours restants sont visibles dans Mon compte. Les anciennes sessions doivent se reconnecter avec l’A2F.

À la prochaine connexion, le mot de passe est vérifié avant de demander le code A2F. Cette deuxième étape expire après cinq minutes. Cinq codes incorrects imposent une attente de cinq minutes. Pour désactiver la protection, confirmez le mot de passe et un code de l’application ou de secours ; les anciennes clés et les codes de secours sont ensuite supprimés. L’activation ou la désactivation concerne uniquement votre propre compte.

Utilisez HTTPS pour accéder à votre instance depuis le réseau. Les clés A2F sont chiffrées avec une clé dérivée de `DJANGO_SECRET_KEY` : sauvegardez aussi votre configuration `.env` dans un emplacement privé distinct des archives. La sauvegarde de la base seule ne suffit pas à récupérer ces clés si ce secret est perdu. Références techniques : [PyOTP](https://pyauth.github.io/pyotp/) et [sessions Django](https://docs.djangoproject.com/en/5.2/topics/auth/default/).

Le bouton de version ouvre une fenêtre indiquant la version affichée et celle du serveur. Après avoir enregistré les formulaires en cours, cliquez sur Recharger l’application. Le rechargement conserve les données déjà enregistrées.

## Outils et téléphone

Les outils sont accessibles à tous : ils calculent sans enregistrer d’opération. La liste des copropriétaires peut préremplir les calculs. Le simulateur de majorité ne remplace ni le choix de la majorité applicable ni le procès-verbal d’une AG.

Sur téléphone, utilisez le bouton de menu en haut. La version en bas de page propose de recharger l’application. L’installation PWA exige HTTPS (sauf localhost). Les fonctions privées nécessitent une connexion au serveur. L’affichage est contrôlé dans des navigateurs à plusieurs largeurs ; les comportements propres à Safari et à un téléphone réel restent à vérifier sur votre appareil.

L’icône de téléchargement à côté de Mon compte permet d’installer Copro. Le navigateur ouvre sa fenêtre d’installation lorsqu’elle est disponible ; sinon, des indications expliquent comment ajouter l’application depuis son menu (sur iPhone/iPad : Safari → Partager → Sur l’écran d’accueil). L’icône disparaît dans l’application déjà ouverte en mode installé. Il n’y a pas de fichier APK à télécharger.

La connexion adopte un bandeau compact sur petit écran pour laisser le formulaire accessible. Les listes de copropriétaires, lots, paiements et mouvements sont des cartes avec leurs libellés, en grille sur ordinateur et empilées sur téléphone. Le menu s’ouvre au-dessus du contenu, possède un bouton Fermer et conserve son défilement propre. Les formulaires longs défilent sous leur en-tête, avec un espace adapté à la hauteur visible. Les champs tactiles évitent le zoom automatique de saisie sans désactiver le zoom manuel.

## Documents individuels et départ d’un copropriétaire

1. Dans **Gestion immeuble**, cliquez sur un nom ou sur un numéro de lot pour ouvrir son dossier. Un membre peut aussi ouvrir **Mes documents et demandes** depuis la vue d’ensemble.
2. Administrateur : cliquez sur **Publier une information**, choisissez la visibilité. Réservez « Technique du lot » aux plans, notices et pièces transmissibles. Choisissez « Personnel » pour un appel de charges PDF, un courrier nominatif ou une demande de relevé.
3. Pour une demande, choisissez son destinataire et éventuellement une échéance. Le destinataire utilise **Répondre** pour joindre son relevé et ses justificatifs. L’administrateur peut ensuite **Clôturer la demande**. Les réponses sont conservées.
4. Avant une vente, créez le compte du nouveau propriétaire. Dans le dossier d’un lot, cliquez sur **Transmettre des lots** ; sélectionnez tous les lots concernés, la date effective (pas de date future) et la référence de l’acte ou de la passation. Vérifiez l’aperçu, puis confirmez.
5. Le nouvel arrivant voit les pièces techniques des lots, mais pas les appels et réponses personnels du vendeur. Les paiements et appels passés gardent leur rattachement d’origine. Aucun solde ni dette n’est transféré automatiquement.
6. Après son dernier lot, le vendeur sans rôle administrateur se connecte à ses seules archives personnelles. Pour conserver cet accès, ne désactivez pas son compte. Vérifiez séparément les droits administrateur dans **Administration**.

Une publication conserve son type, son lot et son destinataire après création : pour une autre destination, créez une nouvelle publication. Les pièces déposées sont conservées lors de l’édition. Les documents communs du fil restent partagés avec les membres actuels.
