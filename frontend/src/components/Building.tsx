import {Dossier} from './Dossier';
import {useState} from 'react';
import {Icon} from './ui';
import {ResetAccess} from './ResetAccess';
import {EditForm,Table,EditButton,type Row,type Field,Empty} from './Common';

export function Building({section,data,admin,onChange,user}:{section:string;data:Row;admin:boolean;onChange:()=>void;user:Row}){
 const[editing,setEditing]=useState<Row|null>(null),[search,setSearch]=useState(''),[reset,setReset]=useState<Row|null>(null);
 const[dossier,setDossier]=useState<number|null>(null);
 const owners=section==='owners';
 const items=(owners?data.owners:data.lots).filter((r:Row)=>`${r.name||r.number} ${r.email||r.description||''}`.toLowerCase().includes(search.toLowerCase()));
 const fields:Field[]=owners?[
  {key:'first_name',label:'Prénom',required:true,max:100},{key:'last_name',label:'Nom',required:true,max:100},
  {key:'email',label:'Courriel et identifiant de connexion',type:'email',required:true,max:254},{key:'phone',label:'Téléphone',type:'tel',max:30},
  ...(!editing?.id?[{key:'password',label:'Mot de passe initial',type:'password',required:true,max:128,help:'12 caractères minimum. Communiquez les accès à la personne par un canal adapté.'} as Field]:[]),
  {key:'active',label:'Compte actif',type:'checkbox'},
 ]:[{key:'number',label:'Numéro du lot',required:true,max:30},{key:'description',label:'Description',max:200},
  {key:'shares',label:'Tantièmes',type:'number',required:true},
  ...(!editing?.id?[{key:'owner',label:'Copropriétaire actuel',type:'select',options:data.owners.filter((o:Row)=>o.active)} as Field]:[]),
 ];
 return <>
  <div className="s-toolbar"><input type="search" aria-label={owners?'Rechercher un copropriétaire':'Rechercher un lot'} placeholder="Rechercher…" value={search} onChange={e=>setSearch(e.target.value)}/>{admin&&<button className="button primary" onClick={()=>setEditing(owners?{active:true}:{shares:'',owner:''})}>{owners?'Ajouter un copropriétaire':'Ajouter un lot'}</button>}</div>
  <div className="s-card"><Table headers={owners?['Copropriétaire','Contact','Lots','Accès',...(admin?['']:[])]:['Lot','Description','Tantièmes','Copropriétaire',...(admin?['']:[])]} rows={items.map((r:Row)=>owners?[
   <strong>{admin||user.owner===r.id?<button className="s-dossier-link" onClick={()=>setDossier(r.id)}>{r.name} ↗</button>:r.name}</strong>,<>{r.email}<small>{r.phone}</small></>,data.lots.filter((l:Row)=>l.owner===r.id).map((l:Row)=>l.number).join(', ')||'—',<span className="s-tag">{r.active?(r.admin?'Administrateur':'Lecture seule'):'Désactivé'}</span>,...(admin?[<div className="s-record-actions"><EditButton label={`Modifier ${r.name}`} onClick={()=>setEditing(r)}/>{r.active&&r.has_access&&<button className="button secondary s-edit-button" aria-label={`Réinitialiser les accès de ${r.name}`} title="Réinitialiser et préparer un courriel" onClick={()=>setReset(r)}><Icon name="refresh" size={18}/></button>}</div>]:[]),
  ]:[<strong>{admin||user.owner===r.owner?<button className="s-dossier-link" onClick={()=>setDossier(r.id)}>Lot {r.number} ↗</button>:r.number}</strong>,r.description,moneyShares(r.shares),data.owners.find((o:Row)=>o.id===r.owner)?.name||'À affecter',...(admin?[<EditButton label={`Modifier le lot ${r.number}`} onClick={()=>setEditing(r)}/>]:[])])}/></div>
  {dossier!==null&&<Dossier kind={section} id={dossier} data={data} user={user} onClose={()=>setDossier(null)} onChanged={onChange}/>}
  {reset&&<ResetAccess owner={reset} loginUrl={data.building.login_url||new URL('/connexion',window.location.origin).href} onClose={()=>setReset(null)} onChanged={onChange}/>}
  {!data.owners.length&&owners&&<Empty>Créez les copropriétaires avec leur courriel, puis affectez leurs lots.</Empty>}
  {editing&&<EditForm title={owners?(editing.id?'Modifier le copropriétaire':'Ajouter un copropriétaire'):(editing.id?'Modifier le lot':'Ajouter un lot')} path={`${section}${editing.id?`/${editing.id}`:''}`} fields={fields} initial={editing} onClose={()=>setEditing(null)} onDone={()=>{setEditing(null);onChange();}} help={!owners?'Le lot conserve son identité. Pour changer de propriétaire, ouvrez le dossier puis « Transmettre des lots » ; les paiements et appels déjà enregistrés conservent leur propriétaire d’origine.':undefined}/>}
 </>;
}
const moneyShares=(v:string)=>Number(v).toLocaleString('fr-FR');
