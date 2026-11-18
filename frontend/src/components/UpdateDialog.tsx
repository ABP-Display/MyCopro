import {useEffect,useState} from 'react';
import {refreshApplication} from '../pwa';
import {Modal} from './Common';
import {Icon} from './ui';
import './account-security.css';

export function UpdateDialog({onClose}:{onClose:()=>void}){
 const[latest,setLatest]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false),[checking,setChecking]=useState(true);
 useEffect(()=>{const controller=new AbortController();fetch('/version.json',{cache:'no-store',signal:controller.signal}).then(async r=>{if(!r.ok)throw new Error();const d=await r.json();if(!/^\d{4}\.\d{2}\.\d{2}\.\d{4}$/.test(d.version))throw new Error();setLatest(d.version);}).catch(e=>{if(e.name!=='AbortError')setError('La version du serveur n’a pas pu être vérifiée. Vous pouvez réessayer le rechargement.');}).finally(()=>setChecking(false));return()=>controller.abort();},[]);
 return <Modal title="Version & mise à jour" busy={busy} onClose={()=>{if(!busy)onClose();}}><div className="update-intro"><span className="account-emblem"><Icon name="refresh" size={26}/></span><div><h3>{checking?'Vérification de la version…':latest&&latest!==__APP_VERSION__?'Une nouvelle version est disponible':latest?'Votre application est à jour':'Vérifier votre application'}</h3><p>Retrouvez les dernières améliorations de Copro.</p></div></div><dl className="update-versions"><div><dt>Version ouverte</dt><dd>{__APP_VERSION__}</dd></div><div><dt>Version du serveur</dt><dd>{checking?'Vérification…':latest||'Indisponible'}</dd></div></dl><div className="update-notice"><Icon name="folder"/><p>Enregistrez vos formulaires avant de continuer. Le rechargement ferme la page en cours ; vos données déjà enregistrées sont conservées.</p></div>{error&&<p className="alert" role="alert">{error}</p>}<div className="update-actions"><button className="button secondary" disabled={busy} onClick={onClose}>Plus tard</button><button className="button primary" disabled={busy||checking} onClick={async()=>{setBusy(true);setError('');try{await refreshApplication();}catch(e){setError((e as Error).message);setBusy(false);}}}><Icon name="refresh" size={16}/>{busy?'Mise à jour…':'Recharger l’application'}</button></div></Modal>;
}
