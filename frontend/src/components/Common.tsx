import {useEffect,useRef,useState,type ReactNode} from 'react';
import {api,newOperationId} from '../api';
export type Row=Record<string,any>;
export const money=(value:string|number)=>Number(value||0).toLocaleString('fr-FR',{style:'currency',currency:'EUR'});
export const today=()=>new Date().toLocaleDateString('en-CA',{timeZone:'Europe/Paris'});
export const dateLabel=(value:string)=>new Date(`${value.slice(0,10)}T12:00:00`).toLocaleDateString('fr-FR');
export function Empty({children}:{children:ReactNode}){return <p className="s-empty">{children}</p>;}
export function Modal({title,onClose,children}:{title:string;onClose:()=>void;children:ReactNode}){
 const dialog=useRef<HTMLDialogElement>(null);
 useEffect(()=>{dialog.current?.showModal();return()=>dialog.current?.close();},[]);
 return <dialog ref={dialog} className="s-dialog" aria-label={title} onCancel={e=>{e.preventDefault();onClose();}}><header><h2>{title}</h2><button className="button secondary" onClick={onClose}>Fermer</button></header><div className="s-dialog-body">{children}</div></dialog>;
}
export type Field={key:string;label:string;type?:string;required?:boolean;options?:Row[];readonly?:boolean;max?:number;help?:string};
export function Fields({fields,value,setValue}:{fields:Field[];value:Row;setValue:(value:Row)=>void}){
 return <div className="s-fields">{fields.map(f=><label key={f.key} className={f.type==='textarea'?'s-full':''}>{f.label}{f.type==='select'?<select required={f.required} value={value[f.key]??''} onChange={e=>setValue({...value,[f.key]:e.target.value})}><option value="">Choisir…</option>{f.options?.map(o=><option key={o.id} value={o.id}>{o.name}</option>)}</select>:f.type==='checkbox'?<input type="checkbox" checked={!!value[f.key]} onChange={e=>setValue({...value,[f.key]:e.target.checked})}/>:f.type==='textarea'?<textarea required={f.required} maxLength={f.max||15000} rows={6} value={value[f.key]??''} onChange={e=>setValue({...value,[f.key]:e.target.value})}/>:<input type={f.type||'text'} required={f.required} readOnly={f.readonly} step={f.type==='number'?'0.01':undefined} maxLength={f.max||150} autoComplete={f.type==='password'?'new-password':undefined} value={value[f.key]??''} onChange={e=>setValue({...value,[f.key]:e.target.value})}/>} {f.help&&<small>{f.help}</small>}</label>)}</div>;
}
export function EditForm({title,path,fields,initial,onClose,onDone,help}:{title:string;path:string;fields:Field[];initial:Row;onClose:()=>void;onDone:()=>void;help?:string}){
 const[value,setValue]=useState(initial),[busy,setBusy]=useState(false),[error,setError]=useState(''),[token]=useState(newOperationId);
 return <Modal title={title} onClose={onClose}><form onSubmit={async e=>{e.preventDefault();setBusy(true);setError('');try{await api(path,'POST',{...value,request_id:token});onDone();}catch(e){setError((e as Error).message);}finally{setBusy(false);}}}>{help&&<p className="s-hint">{help}</p>}{error&&<p className="alert" role="alert">{error}</p>}<fieldset disabled={busy}><Fields fields={fields} value={value} setValue={setValue}/></fieldset><footer><button className="button primary" disabled={busy}>{busy?'Enregistrement…':'Enregistrer'}</button></footer></form></Modal>;
}
export function Table({headers,rows}:{headers:string[];rows:ReactNode[][]}){return <div className="s-table"><table><thead><tr>{headers.map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{rows.map((row,i)=><tr key={i}>{row.map((cell,j)=><td key={j}>{cell}</td>)}</tr>)}</tbody></table>{!rows.length&&<Empty>Aucun élément à afficher.</Empty>}</div>;}
export function Metrics({items}:{items:[string,string|number][]}){return <div className="s-metrics">{items.map(([label,value])=><article key={label}><span>{label}</span><strong>{value}</strong></article>)}</div>;}
