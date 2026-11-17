import { useEffect, useState } from "react";
import { api } from "../api";

type Movement = {
  id: number; number: number; year: string; date: string; label: string;
  reference: string; incoming: string; outgoing: string; balance: string;
  payer: string; supplier: string; document: number | null;
  paid_for: {lot:string; call:string; amount:string}[];
  counterparts: {account: string; label: string; person: string}[];
};
type Statement = {
  opening: string; incoming: string; outgoing: string; closing: string;
  items: Movement[]; page: number; pages: number; count: number;
};
const money = (value: string) => Number(value).toLocaleString("fr-FR", {style:"currency", currency:"EUR"});
const day = (value: string) => new Date(`${value}T12:00:00`).toLocaleDateString("fr-FR");

export function BankMovements({bankId, endDate}: {bankId: number; endDate: string}) {
  const [start, setStart] = useState(`${endDate.slice(0,4)}-01-01`);
  const [end, setEnd] = useState(endDate);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Statement | null>(null);
  const [error, setError] = useState("");
  useEffect(()=>{
    let live = true;
    setData(null); setError("");
    api<Statement>(`finance/banks/${bankId}/movements?from=${start}&to=${end}&page=${page}`)
      .then(value=>{if(live) setData(value);})
      .catch(e=>{if(live) setError(e.message);});
    return ()=>{live=false;};
  }, [bankId,start,end,page]);
  return <div className="bank-statement">
    <p className="ops-muted">Les encaissements augmentent le solde et les décaissements le diminuent. Ce suivi provient de votre comptabilité ; vérifiez-le avec le relevé de la banque. Un appel de charges non payé n’est pas une entrée d’argent.</p>
    <div className="ops-toolbar">
      <label className="ops-field">Du<input type="date" required value={start} onChange={e=>{if(e.target.value){setStart(e.target.value);setPage(1);}}}/></label>
      <label className="ops-field">Au<input type="date" required value={end} onChange={e=>{if(e.target.value){setEnd(e.target.value);setPage(1);}}}/></label>
    </div>
    {error && <p className="alert" role="alert">{error}</p>}
    {!data && !error && <p role="status">Chargement des mouvements…</p>}
    {data && <>
      <dl className="ops-facts">
        <div><dt>Solde avant la période</dt><dd>{money(data.opening)}</dd></div>
        <div><dt>Entrées sur la période</dt><dd>{money(data.incoming)}</dd></div>
        <div><dt>Sorties sur la période</dt><dd>{money(data.outgoing)}</dd></div>
        <div><dt>Solde au {day(end)}</dt><dd>{money(data.closing)}</dd></div>
      </dl>
      <div className="ops-table-wrap"><table>
        <thead><tr><th>Date</th><th>Opération et justificatif</th><th>Entrée</th><th>Sortie</th><th>Solde après opération</th></tr></thead>
        <tbody>{data.items.map(row=><tr key={row.id}>
          <td>{day(row.date)}<small>Écriture {row.number} · {row.year}</small></td>
          <td>{row.label}<small>{row.reference}</small>
            {(row.payer || row.supplier) && <small>{row.payer ? `Paiement de ${row.payer}` : `Facture · ${row.supplier}`}</small>}
            {row.paid_for.map((link,i)=><small key={`lot-${i}`}>Lot {link.lot} · {link.call} : {money(link.amount)}</small>)}
            {row.counterparts.map((c,i)=><small key={i}>{c.account} · {c.person || c.label}</small>)}
            {row.document && <a href={`/api/documents/items/${row.document}/download/`}>Voir la facture</a>}
          </td>
          <td>{Number(row.incoming) ? money(row.incoming) : "—"}</td>
          <td>{Number(row.outgoing) ? money(row.outgoing) : "—"}</td>
          <td>{money(row.balance)}</td>
        </tr>)}</tbody>
      </table></div>
      {!data.items.length && <p className="ops-empty">Aucun mouvement sur cette période.</p>}
      <div className="ops-actions">
        <button className="button secondary" disabled={page<=1} onClick={()=>setPage(p=>p-1)}>Précédent</button>
        <span aria-live="polite">Page {data.page} / {data.pages} · {data.count} mouvements</span>
        <button className="button secondary" disabled={page>=data.pages} onClick={()=>setPage(p=>p+1)}>Suivant</button>
      </div>
    </>}
  </div>;
}
