import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { Icon } from "./ui";
import "./document-tools.css";
type Data = Record<string, any>;
type Fields = Record<string, string>;

export function DocumentTemplates() {
  const [catalog, setCatalog] = useState<Data | null>(null);
  const [selected, setSelected] = useState("");
  const [recipient, setRecipient] = useState("");
  const [fields, setFields] = useState<Fields | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [reviewed, setReviewed] = useState(false);
  const [saved, setSaved] = useState<Data | null>(null);
  const sequence = useRef(0);
  useEffect(() => { let live=true; api<Data>("documents/templates").then(data=>{if(live)setCatalog(data);}).catch(e=>{if(live)setError(e.message);}); return()=>{live=false;}; }, []);
  const item = catalog?.items.find((row: Data) => row.id === selected);
  useEffect(() => {
    const id = ++sequence.current;
    setFields(null); setSaved(null); setReviewed(false); setError("");
    if (!selected || (selected === "reminder" && !recipient)) { setLoading(false); return; }
    setLoading(true);
    const query = recipient ? `?${item?.target === "supplier" ? "supplier" : "owner"}=${recipient}` : "";
    api<{fields: Fields}>(`documents/templates/${selected}${query}`)
      .then(data => { if (sequence.current === id) setFields(data.fields); })
      .catch(e => { if (sequence.current === id) setError(e.message); })
      .finally(() => { if (sequence.current === id) setLoading(false); });
    return () => { ++sequence.current; };
  }, [selected, recipient]);
  function update(key: string, value: string) {
    setFields(previous => previous ? {...previous, [key]:value} : null);
    setReviewed(false); setSaved(null);
  }
  return <section className="template-space">
    <div className="tool-intro"><Icon name="file"/><p>Choisissez un modèle, reprenez un destinataire et complétez le texte. Un aperçu s’affiche avant la création du PDF. Les documents restent privés dans la bibliothèque ; aucun courrier n’est signé ni envoyé.</p></div>
    <div className="template-catalog">{catalog?.items.map((row: Data) => <button key={row.id} type="button" disabled={busy} aria-pressed={selected===row.id} className={`template-card ${selected===row.id ? "selected" : ""}`} onClick={()=>{setSelected(row.id);setRecipient("");}}><Icon name="file"/><strong>{row.title}</strong><span>{row.description}</span></button>)}</div>
    {error && <div className="alert" role="alert">{error}</div>}
    {!catalog && !error && <p role="status">Chargement des modèles…</p>}
    {item && <section className="panel template-editor">
      <h2>{item.title}</h2>
      <label className="template-recipient">{item.target === "supplier" ? "Reprendre un fournisseur" : "Reprendre un copropriétaire"}
        <select disabled={busy} value={recipient} onChange={e=>setRecipient(e.target.value)}>
          <option value="">{selected === "reminder" ? "Choisir un copropriétaire…" : "Destinataire libre ou collectif"}</option>
          {(item.target === "supplier" ? catalog?.suppliers : catalog?.owners)?.map((row: Data)=><option key={row.id} value={row.id}>{row.name}</option>)}
        </select>
      </label>
      <p className="template-help">Le choix d’un modèle ou d’un destinataire recharge le texte proposé. Les champs restent modifiables avant création.</p>
      {loading && <p role="status">Préparation du document…</p>}
      {selected === "reminder" && !recipient && <p>Choisissez une personne pour reprendre son solde actuel. Vérifiez les échéances et les règlements en cours avant toute relance.</p>}
      {fields && <div className="template-workspace">
        <form className="template-form" onSubmit={async e=>{
          e.preventDefault(); setBusy(true); setError("");
          try {setSaved(await api<Data>(`documents/templates/${selected}`,"POST",{fields,reviewed}));}
          catch(error){setError((error as Error).message);} finally{setBusy(false);}
        }}>
          <fieldset disabled={busy}>
            <label>Titre dans la bibliothèque<input required maxLength={150} value={fields.title} onChange={e=>update("title",e.target.value)}/></label>
            <label>Date du courrier<input required type="date" value={fields.date} onChange={e=>update("date",e.target.value)}/></label>
            <label>Destinataire<input required maxLength={300} value={fields.recipient} onChange={e=>update("recipient",e.target.value)}/></label>
            <label>Adresse ou courriel du destinataire<textarea rows={3} maxLength={1000} value={fields.recipient_address} onChange={e=>update("recipient_address",e.target.value)}/></label>
            <label>Objet<input required maxLength={200} value={fields.subject} onChange={e=>update("subject",e.target.value)}/></label>
            <label>Contenu à compléter<textarea required rows={12} maxLength={20000} value={fields.body} onChange={e=>update("body",e.target.value)}/></label>
            <label>Nom ou qualité du signataire<input required maxLength={500} value={fields.signature} onChange={e=>update("signature",e.target.value)}/></label>
            <label className="template-review"><input type="checkbox" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/>J’ai relu le destinataire et le contenu, et remplacé les mentions à compléter.</label>
            <button className="button primary" disabled={!reviewed || busy || !!saved}>{busy ? "Création…" : "Créer le PDF privé"}</button>
          </fieldset>
        </form>
        <article className="template-preview" aria-label="Aperçu du courrier"><p className="eyebrow">APERÇU DU CONTENU</p><p>{fields.recipient}<br/>{fields.recipient_address}</p><p>{fields.date}</p><h3>{fields.subject}</h3><p>{fields.body}</p><p>{fields.signature}</p><small>Les coordonnées de la copropriété sont ajoutées dans le PDF.</small></article>
      </div>}
      {saved && <div className="template-success" role="status"><strong>Document créé dans « Courriers préparés ».</strong><p>Il est réservé aux gestionnaires. Son partage éventuel se fait depuis la bibliothèque.</p><a className="button secondary" href={saved.download}>Télécharger le PDF</a></div>}
    </section>}
    <p className="template-help">Les convocations, pouvoirs, formulaires de vote, procès-verbaux et annexes comptables se préparent dans les parcours AG et comptabilité : ils reprennent les pièces, votes et comptes du dossier.</p>
  </section>;
}
