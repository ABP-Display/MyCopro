import {useId,useState} from 'react';
import {api,newOperationId} from '../api';
import {Modal,type Row} from './Common';
import {Icon} from './ui';

function password(){const alphabet='ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@-';const values=crypto.getRandomValues(new Uint32Array(16));return 'Cp7!'+Array.from(values,n=>alphabet[n%alphabet.length]).join('');}
export function ResetAccess({owner,loginUrl,onClose,onChanged}:{owner:Row;loginUrl:string;onClose:()=>void;onChanged:()=>void}){
 const previewId=useId();
 const[chosen]=useState(password),[token]=useState(newOperationId),[result,setResult]=useState<Row|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const person=result||{name:owner.name,email:owner.email,login:owner.email,login_url:loginUrl};
 const subject='Vos nouveaux accès à Copro.';
 const body=`Bonjour ${person.name},\n\nVos accès à l’espace de votre copropriété ont été réinitialisés.\n\nLien de connexion : ${person.login_url}\nIdentifiant : ${person.login}\nNouveau mot de passe : ${chosen}\n\nAprès votre connexion, vous pouvez choisir votre propre mot de passe dans « Mon compte ». Si l’A2F est activée, votre code d’authentification reste nécessaire.\n\nÀ bientôt,\nLe syndic bénévole`;
 const mailto=`mailto:${encodeURIComponent(person.email)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
 return <Modal title="Réinitialiser les accès" busy={busy} onClose={onClose}><div className="reset-recipient"><span className="account-emblem"><Icon name="mail"/></span><div><strong>{owner.name}</strong><small>{owner.email}</small></div></div>{error&&<p className="alert" role="alert">{error}</p>}
  {result?<p className="account-success" role="status">Le nouveau mot de passe est enregistré. Le courriel est prêt à ouvrir dans votre messagerie ; aucun message n’a été envoyé automatiquement.</p>:<p className="s-hint">Vérifiez les accès et le message ci-dessous. Le mot de passe actuel reste valable jusqu’à votre confirmation.</p>}
  <dl className="reset-details"><div><dt>Lien de connexion</dt><dd>{person.login_url}</dd></div><div><dt>Identifiant</dt><dd>{person.login}</dd></div><div><dt>Nouveau mot de passe</dt><dd><code>{chosen}</code></dd></div></dl>
  <div className="reset-preview"><label htmlFor={previewId}>Courriel préparé</label><textarea id={previewId} rows={11} readOnly value={body}/></div>
  <div className="reset-actions">{!result?<button className="button primary" disabled={busy} onClick={async()=>{setBusy(true);setError('');try{setResult(await api(`owners/${owner.id}/reset-access`,'POST',{password:chosen,request_id:token}));onChanged();}catch(e){setError((e as Error).message);}finally{setBusy(false);}}}>{busy?'Réinitialisation…':'Confirmer et préparer le courriel'}</button>:<a className="button primary" href={mailto}><Icon name="mail" size={18}/>Ouvrir le courriel dans ma messagerie</a>}</div>
 </Modal>;
}
