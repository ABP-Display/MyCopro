import { useEffect, useRef, useState } from "react";
import { api, newOperationId } from "../api";
import "./document-validation.css";
type Row = Record<string, any>;
const statuses: Record<string,string> = {unreviewed:"Relecture métier à réaliser",approved:"Relecture métier enregistrée",rejected:"Corrections demandées",withdrawn:"Validation retirée",stale:"Dossier modifié : nouvelle relecture requise"};

export function DocumentValidation({kind,id,document,revision=""}:{kind:"accounting"|"assembly"|"minutes";id:number|string;document:string;revision?:string}) {
  const [data,setData]=useState<Row|null>(null),[error,setError]=useState(""),[busy,setBusy]=useState(false),[success,setSuccess]=useState("");
  const [checks,setChecks]=useState<Record<string,boolean>>({});
  const [formKey,setFormKey]=useState(0);
  const sequence=useRef(0),operation=useRef(newOperationId());
  const path=`documents/validation/${kind}/${id}`;
  async function load(){
    const run=++sequence.current;
    try {const next=await api<Row>(path);if(run!==sequence.current)return;setData(next);setChecks({});setError("");setFormKey(k=>k+1);operation.current=newOperationId();}
    catch(e){if(run===sequence.current)setError((e as Error).message);}
  }
  useEffect(()=>{setData(null);setSuccess("");void load();return()=>{sequence.current++;};},[kind,id,revision]);
  async function decide(event:React.FormEvent<HTMLFormElement>){
    event.preventDefault();if(busy||!data)return;setBusy(true);setError("");setSuccess("");
    const values=Object.fromEntries(new FormData(event.currentTarget));
    try {await api(path,"POST",{...values,checks,source_hash:data.source_hash,declaration_confirmed:values.declaration_confirmed==="on",proof:Number(values.proof),request_id:operation.current});setSuccess("Décision et rapport de relecture enregistrés. Les signatures et envois restent à réaliser.");await load();}
    catch(e){setError((e as Error).message);}finally{setBusy(false);}
  }
  const href=`/api/${path}/export/${document}/`;
  return <section className="document-validation ag-no-print">
    <div className="document-validation-heading"><div><p className="eyebrow">Avant utilisation officielle</p><h3>{data?statuses[data.status]:"Validation des documents"}</h3><p>Les contrôles automatiques préparent la relecture. Une personne doit examiner les PDF, les justificatifs et les cas particuliers.</p></div><button className="button secondary" type="button" disabled={busy} onClick={()=>void load()}>Actualiser</button></div>
    {error&&<p className="alert error" role="alert">{error}</p>}{success&&<p className="alert success" role="status">{success}</p>}
    {data&&<>
      {data.errors.length>0&&<div className="alert error"><strong>Édition validée bloquée</strong><ul>{data.errors.map((text:string)=><li key={text}>{text}</li>)}</ul></div>}
      <div className="document-validation-actions"><a className="button secondary" href={href}>Télécharger le PDF de travail</a>{data.status==="approved"&&<a className="button primary" href={href+"?official=1"}>Télécharger l’édition relue</a>}</div>
      <p className="muted">Modèle {data.model_version} · empreinte <span className="document-validation-hash">{data.source_hash}</span>. Le PDF de travail porte toujours la mention « PROJET ».</p>
      {data.can_review&&<details><summary>Enregistrer une relecture effectivement réalisée</summary><p>Faire relire le PDF téléchargé, déposer le rapport signé dans Documents, puis consigner sa conclusion ici. Ne cochez que les points vérifiés. Ceci enregistre une déclaration de relecture et ne constitue pas une certification du logiciel.</p>
        <form key={formKey} onSubmit={decide} onChange={()=>{operation.current=newOperationId();}}><fieldset disabled={busy}>
          <div className="document-validation-grid"><label>Nom du relecteur<input name="reviewer" required maxLength={200}/></label><label>Qualité / rôle<input name="qualification" required maxLength={200} placeholder="Ex. contrôleur des comptes, syndic, comptable"/></label><label>Date de relecture<input name="reviewed_on" type="date" required max={new Date().toLocaleDateString("en-CA",{timeZone:"Europe/Paris"})}/></label><label>Rapport de relecture signé<select name="proof" required defaultValue=""><option value="">Choisir une version dans Documents</option>{data.versions.map((v:Row)=><option key={v.id} value={v.id}>{v.title} · {v.filename} · version {v.id}</option>)}</select></label></div>
          <div className="document-validation-checks">{Object.entries(data.checks).map(([key,label])=><label key={key}><input type="checkbox" checked={checks[key]===true} onChange={e=>{operation.current=newOperationId();setChecks({...checks,[key]:e.target.checked});}}/>{String(label)}</label>)}</div>
          <label>Conclusion et réserves<textarea name="observations" required maxLength={10000} rows={3}/></label>
          <label>Décision<select name="verdict" required defaultValue="rejected"><option value="rejected">Corrections à réaliser</option><option value="approved" disabled={data.errors.length>0}>Validation après relecture complète</option>{data.history.length>0&&<option value="withdrawn">Retirer une validation / décision</option>}</select></label>
          <label className="document-validation-attestation"><input name="declaration_confirmed" type="checkbox" required/>J’atteste que la relecture déclarée a été effectuée par la personne indiquée, sur cette version du dossier, et que le rapport joint justifie la décision.</label>
          <button className="button primary" type="submit">{busy?"Enregistrement…":"Enregistrer la décision"}</button>
        </fieldset></form>
      </details>}
      {data.history.length>0&&<details><summary>Historique des relectures ({data.history.length})</summary>{data.history.map((r:Row)=><article className="document-validation-history" key={r.id}><strong>{statuses[r.verdict]||({approved:"Relecture enregistrée",rejected:"Corrections demandées",withdrawn:"Validation retirée"} as Record<string,string>)[r.verdict]}</strong><p>{r.reviewer} · {r.qualification} · {r.reviewed_on} · rapport version {r.proof_id}</p><p>{r.observations}</p><small>Modèle {r.model_version} · {r.source_hash}</small></article>)}</details>}
    </>}
  </section>;
}
