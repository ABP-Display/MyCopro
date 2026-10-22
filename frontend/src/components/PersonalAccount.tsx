import { useEffect, useState } from "react";
import { api } from "../api";
import "./document-tools.css";

type Data = Record<string, any>;
const money = (value: string) => new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(Number(value));

export function PersonalAccount() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [range, setRange] = useState({ from: "", to: "" });
  const [page, setPage] = useState(1);
  const query = new URLSearchParams({ ...range, page: String(page) }).toString();
  useEffect(() => {
    let active = true;
    setData(null); setError("");
    api<Data>(`operations/my-account?${query}`)
      .then(value => { if (active) setData(value); })
      .catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [query]);
  const exportUrl = (format: string) => `/api/operations/my-account/export/?${new URLSearchParams({ ...range, format })}`;
  return <section className="panel ops-surface personal-account">
    <div className="panel-heading">
      <div><h2>Mon compte copropriétaire</h2><p>Vos mouvements personnels restent privés.</p></div>
      {data && <div><small>Solde actuel</small><strong>{money(data.balance)}</strong></div>}
    </div>
    <form className="account-filters" onSubmit={e => { e.preventDefault(); setPage(1); setRange({ from, to }); }}>
      <label>Du<input type="date" value={from} max={to || data?.date} onChange={e => setFrom(e.target.value)} /></label>
      <label>Au<input type="date" value={to} min={from} max={data?.date} onChange={e => setTo(e.target.value)} /></label>
      <button className="button secondary">Afficher la période</button>
      <button type="button" className="button secondary" onClick={() => { setFrom(""); setTo(""); setRange({from:"",to:""}); setPage(1); }}>Tout l’historique</button>
    </form>
    {error && <p role="alert" className="alert">{error}</p>}
    {!data && !error && <p role="status">Chargement du relevé…</p>}
    {data && <>
      <p>{Number(data.balance) > 0 ? "Solde débiteur à vérifier avec le gestionnaire." : Number(data.balance) < 0 ? "Votre compte présente un crédit." : "Votre compte est équilibré."}</p>
      <dl className="account-summary">
        <div><dt>Solde au début de la période</dt><dd>{money(data.opening_balance)}</dd></div>
        <div><dt>Débits de la période</dt><dd>{money(data.total_debit)}</dd></div>
        <div><dt>Crédits de la période</dt><dd>{money(data.total_credit)}</dd></div>
        <div><dt>Solde au {data.to}</dt><dd>{money(data.closing_balance)}</dd></div>
      </dl>
      <div className="document-tool-actions">
        <a className="button secondary" href={exportUrl("pdf")}>Télécharger mon relevé PDF</a>
        <a className="button secondary" href={exportUrl("csv")}>Exporter les mouvements CSV</a>
      </div>
      <div className="table-scroll"><table>
        <thead><tr><th>Date</th><th>Libellé</th><th>Débit</th><th>Crédit</th></tr></thead>
        <tbody>{data.rows.map((row: Data, i: number) => <tr key={i}><td>{row.date}</td><td>{row.label}</td><td>{money(row.debit)}</td><td>{money(row.credit)}</td></tr>)}
          {!data.rows.length && <tr><td colSpan={4}>Aucun mouvement sur cette période.</td></tr>}
        </tbody>
      </table></div>
      <div className="account-pagination" aria-label="Pages du relevé">
        <button className="button secondary" disabled={page <= 1} onClick={() => setPage(page-1)}>Précédent</button>
        <span aria-live="polite">Page {data.page} / {data.pages} · {data.count} mouvement(s)</span>
        <button className="button secondary" disabled={page >= data.pages} onClick={() => setPage(page+1)}>Suivant</button>
      </div>
      <p className="operations-note">{data.note} Les téléchargements couvrent toute la période sélectionnée, pas seulement la page affichée.</p>
    </>}
  </section>;
}
