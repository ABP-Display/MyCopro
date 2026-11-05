import { Icon } from "./ui";
import { sections } from "./Navigation";

export const categoryHelp: Record<
  string,
  { description: string; advice: string; items: Record<string, string> }
> = {
  operations: {
    description:
      "Suivez les travaux, sinistres et échéances de votre immeuble avec leurs pièces et décisions.",
    advice:
      "Les alertes se basent sur vos données. Relisez les preuves et vérifiez les échéances avant de valider ; aucun courrier ni paiement n’est déclenché automatiquement.",
    items: {
      works:
        "Rassemblez devis, documents, budget et décision d’AG. Comparez les montants avant de retenir un devis.",
      deadlines:
        "Ajoutez une date et une source vérifiée pour chaque obligation applicable à votre immeuble.",
    },
  },
  partners: {
    description:
      "Retrouvez les entreprises, leurs contrats et les pièces à tenir à jour.",
    advice:
      "Créez le fournisseur, puis ses contrats et attestations. Les devis et factures peuvent ensuite reprendre cet annuaire.",
    items: {
      suppliers:
        "Centralisez les contacts et métiers des entreprises, puis choisissez-les dans les devis et factures.",
      contracts:
        "Suivez les dates, coûts déclarés et préavis des contrats avant une éventuelle reconduction.",
      certificates:
        "Conservez les pièces fournisseurs et les dates de validité à vérifier.",
    },
  },
  communication: {
    description:
      "Partagez les informations utiles avec les copropriétaires depuis leur portail.",
    advice:
      "Rédigez d’abord un brouillon, puis publiez le message après relecture. Les annonces sont partagées avec tous les copropriétaires connectés.",
    items: {
      notices:
        "Publiez une annonce, retirez-la pour la corriger et archivez les messages devenus inutiles.",
    },
  },
  assemblies: {
    "description": "Préparez vos résolutions, faites voter le budget ou les travaux, puis conservez le PV et les décisions.",
    "advice": "Suivez les étapes du dossier. Les modèles de budget et travaux préparent un texte à relire ; les votes et preuves restent enregistrés.",
    "items": {
        "prepare": "Créez l’AG, ajoutez vos résolutions ou partez d’un modèle de budget ou de travaux, puis préparez les convocations.",
        "run": "Enregistrez les présences, pouvoirs et votes.",
        "follow": "Relisez le PV, suivez ses notifications et retrouvez les décisions et personnes élues."
    }
},
  tools: {
    description:
      "Vérifiez vos calculs avant de préparer un vote, un appel de fonds ou un budget. Ces outils ne modifient pas la comptabilité.",
    advice:
      "Utilisez le calcul de majorité pour le cas général français, avec les droits de vote corrigés. Les outils de répartition et d’échéancier conservent exactement le total au centime.",
    items: {
      vote: "Distinguez voix exprimées, voix de tous les copropriétaires et nombre de copropriétaires. Le résultat explique le seuil et signale les passerelles vers un second vote.",
      split:
        "Répartissez un montant entre plusieurs parts selon leurs tantièmes ou poids, avec un arrondi contrôlé au centime.",
      installments:
        "Divisez une somme en plusieurs échéances égales. Les éventuels centimes restants sont distribués sur les premières échéances.",
    },
  },
  documents: {
    description:
      "Conservez les documents de la copropriété au même endroit, puis choisissez ceux à partager avec les copropriétaires.",
    advice:
      "Les nouveaux documents sont réservés aux gestionnaires. Le bouton Partager les rend accessibles à tous les copropriétaires connectés ; les anciennes versions restent réservées aux gestionnaires.",
    items: {
      library:
        "Déposez des PDF ou images, retrouvez un document, ajoutez une version et gérez son partage. L’archivage masque un document sans effacer son historique.",
      templates:
        "Préremplissez un courrier, une demande de devis ou d’intervention depuis l’annuaire, corrigez le texte puis créez un PDF privé après relecture.",
      folders:
        "Créez et renommez des dossiers pour organiser les contrats, factures, comptes rendus et autres documents.",
    },
  },
  finance: {
    "description": "Demandez les charges courantes ou exceptionnelles et enregistrez les règlements reçus.",
    "advice": "Commencez par l’appel de charges, puis enregistrez le paiement réellement reçu. Les factures et rapports sont dans Gestion comptable.",
    "items": {
        "calls": "Préparez et vérifiez les montants demandés pour les charges, les travaux ou un appel exceptionnel.",
        "payments": "Choisissez la personne qui a payé, enregistrez son règlement et vérifiez les sommes restant dues.",
        "funding": "Retrouvez le fonds travaux et les avances, avec les décisions et justificatifs nécessaires."
    }
},
  accounting: {
    "description": "Retrouvez ce qui a été reçu, ce qui a été payé et à quoi les sommes ont servi.",
    "advice": "Consultez les comptes, suivez les factures et préparez une fiche de rapport par mois ou trimestre. Les réglages comptables moins fréquents sont dans Opérations avancées.",
    "items": {
        "history": "Historique des comptes, paiements, dépenses et pièces, consultable sans modifier les écritures.",
        "expenses": "Enregistrez les factures communes et leurs règlements.",
        "approvals": "Examinez et validez les dépenses soumises à avis.",
        "reports": "Choisissez une période mensuelle ou trimestrielle et imprimez ou exportez le résultat.",
        "advanced": "Accès secondaire aux reprises, clés de répartition, banques, clôture et états détaillés."
    }
},
  reporting: {
    description:
      "Comprenez vos comptes à partir des opérations enregistrées, puis exportez ou imprimez les résultats.",
    advice:
      "Choisissez un exercice et une période. Les filtres limitent les données affichées ; le budget reste annuel et le bilan est calculé à la date de fin.",
    items: {
      balance:
        "Comparez les débits, crédits et soldes de chaque compte. Utile pour une première vérification de l’ensemble des comptes.",
      aged: "Distinguez les échéances futures, les retards et les crédits à affecter avant de préparer une relance.",
      annexes:
        "Relisez les cinq états calculés et les décomptes individuels, puis imprimez le dossier ou exportez les écritures.",
      auxiliary:
        "Consultez les montants dus ou les avances de chaque copropriétaire : solde avant la période, mouvements et solde final. Ces données individuelles restent privées.",
      "supplier-auxiliary":
        "Retrouvez les dettes et règlements par fournisseur identifié, avec solde avant la période et solde final. Les anciennes écritures sans fournisseur restent signalées séparément.",
      ledger:
        "Retrouvez tous les mouvements d’un compte avec le solde avant la période et son évolution après chaque opération.",
      journal:
        "Relisez les opérations dans l’ordre des dates, avec leurs références et les comptes concernés.",
      income:
        "Comparez les charges et les produits enregistrés pour comprendre le résultat de la période.",
      sheet:
        "Consultez la synthèse des comptes à une date donnée. Cet état ne remplace pas les annexes réglementaires de copropriété.",
      budget:
        "Repérez les écarts entre ce qui était prévu pour l’année et les opérations réellement enregistrées.",
    },
  },
  administration: {
    description:
      "Personnalisez votre copropriété, ses règles de saisie et les accès des personnes qui la gèrent.",
    advice:
      "Commencez par le nom et les coordonnées. Réservez le rôle Gestionnaire aux personnes autorisées à modifier les données ; les autres comptes restent en lecture seule.",
    items: {
      organization:
        "Renseignez le nom et les coordonnées de la copropriété, puis ajustez les paramètres comptables proposés dans les formulaires.",
      journals:
        "Organisez les écritures par famille d’opérations, par exemple achats ou banque, et choisissez le journal proposé par défaut.",
      users:
        "Activez ou désactivez un accès et choisissez le rôle lecture ou gestionnaire. Cette section est réservée à l’administrateur principal.",
      audit:
        "Consultez les opérations comptables et de configuration enregistrées, avec leur date et leur auteur.",
      security:
        "Activez votre application d’authentification, conservez vos codes de secours et gérez votre mot de passe.",
      backups:
        "Suivez les sauvegardes chiffrées de la base et des documents, les restaurations vérifiées et la règle de double authentification des gestionnaires.",
    },
  },
};

export function CategoryOverview({
  category,
  isAdmin,
  onNavigate,
}: {
  category: string;
  isAdmin: boolean;
  onNavigate: (section: string) => void;
}) {
  const group = sections[category];
  const help = categoryHelp[category];
  return (
    <section className="category-overview">
      <div className="category-intro">
        <span className="category-symbol">
          <Icon name={group.icon} size={28} />
        </span>
        <div>
          <p className="eyebrow">POUR BIEN COMMENCER</p>
          <h2>Bien démarrer</h2>
          <p>{help.advice}</p>
        </div>
      </div>
      <div className="category-grid">
        {group.items
          .filter(([key]) => !["users", "backups"].includes(key) || isAdmin)
          .map(([key, label], index) => (
            <button
              key={key}
              className="category-card"
              onClick={() => onNavigate(key)}
            >
              <span className="category-card-number">
                {String(index + 1).padStart(2, "0")}
              </span>
              <h3>{label}</h3>
              <p>{help.items[key]}</p>
              <span className="category-card-link">
                Ouvrir la section <Icon name="arrow" size={16} />
              </span>
            </button>
          ))}
      </div>
    </section>
  );
}
