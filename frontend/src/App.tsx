import {useEffect,useState} from 'react';
import {api} from './api';
import {BrandMark} from './components/BrandMark';
import {Icon,BuildingIllustration} from './components/ui';
import {Building} from './components/Building';
import {Finance} from './components/Finance';
import {Feed} from './components/Feed';
import {Tools} from './components/Tools';
import {Administration} from './components/Administration';
import {Modal,EditForm,Metrics,money,today,type Row} from './components/Common';
import {registerAppWorker,refreshApplication} from './pwa';

const groups=[
 {name:'Gestion immeuble',icon:'building',pages:[['owners','Copropriétaires'],['lots','Lots & tantièmes']]},
 {name:'Gestion financière',icon:'wallet',pages:[['banks','Suivi des comptes'],['charges','Charges courantes'],['funds','Travaux & exceptionnel'],['payments','Paiements des copropriétaires']]},
 {name:'Vie de la copropriété',icon:'message',pages:[['feed','Documents & communication']]},
 {name:'Outils',icon:'calculator',pages:[['split','Répartir un montant'],['installments','Simuler un échéancier'],['vote','Calcul de majorité']]},
];
const descriptions:Record<string,string>={
 overview:'Les informations utiles pour gérer votre immeuble, simplement.',owners:'Retrouvez les personnes de votre immeuble et leurs coordonnées.',lots:'Les lots restent dans l’immeuble. Leurs propriétaires peuvent changer.',
 banks:'Vos comptes, leurs soldes et les opérations qui les font évoluer.',charges:'Partez du montant voté, puis répartissez les charges selon les tantièmes.',funds:'Préparez les appels destinés aux travaux et aux dépenses exceptionnelles.',payments:'Retrouvez les versements de chaque année et les paiements restant à vérifier.',feed:'Un même fil pour les informations, les échanges du syndic et les documents partagés.',split:'Une estimation par tantièmes, avec le détail annuel, trimestriel et mensuel.',installments:'Visualisez les versements nécessaires pour étaler un montant.',vote:'Simulez un vote avec la liste des copropriétaires ou des données libres.',admin:'Coordonnées, catégories, rôles et historique des actions de gestion.',
};
export function App(){
 const[user,setUser]=useState<Row|null>(null),[data,setData]=useState<Row|null>(null),[initializing,setInitializing]=useState(true),[error,setError]=useState(''),[page,setPage]=useState('overview'),[compact,setCompact]=useState(()=>localStorage.getItem('copro-simple-compact')==='1'),[mobile,setMobile]=useState(false),[account,setAccount]=useState(false),[version,setVersion]=useState(false),[updating,setUpdating]=useState(false);
 useEffect(()=>{api('session').then(d=>setUser(d.user)).catch(e=>setError(e.message)).finally(()=>setInitializing(false));registerAppWorker();},[]);
 async function load(){setError('');try{setData(await api('state'));}catch(e){setError((e as Error).message);}}
 useEffect(()=>{if(user)void load();else setData(null);},[user]);
 const go=(next:string)=>{setPage(next);setMobile(false);setError('');window.scrollTo({top:0});};
 const activeGroup=groups.find(g=>g.pages.some(([key])=>key===page));
 const title=page==='overview'?'Votre copropriété, en clair':page==='admin'?'Administration':groups.flatMap(g=>g.pages).find(([key])=>key===page)?.[1]||'Copro.';
 if(initializing)return <main className="boot"><BrandMark/><p>Ouverture de votre espace…</p></main>;
 if(!user)return <Login error={error} onLogin={setUser}/>;
 return <div className={`s-shell ${compact?'s-compact':''}`}>
  {mobile&&<button className="s-nav-backdrop" aria-label="Fermer le menu" onClick={()=>setMobile(false)}/>}
  <aside className={`s-side ${mobile?'s-side-open':''}`} aria-label="Navigation principale">
   <a className="brand" href="/" onClick={e=>{e.preventDefault();go('overview');}}><BrandMark/><span>Copro<span className="brand-dot">.</span></span></a>
   <div className="s-building"><Icon name="building"/><div><strong>{data?.building.name||'Ma copropriété'}</strong><small>Votre espace commun</small></div></div>
   <nav><button className={`s-nav-home ${page==='overview'?'selected':''}`} title="Vue d’ensemble" onClick={()=>go('overview')}><Icon name="grid"/><span>Vue d’ensemble</span></button>{groups.map(g=><section key={g.name}><button className={`s-nav-group ${activeGroup===g?'selected':''}`} title={g.name} onClick={()=>go(g.pages[0][0])}><Icon name={g.icon}/><span>{g.name}</span></button>{(!compact||mobile)&&<div className="s-nav-children">{g.pages.map(([key,label])=><button className={page===key?'selected':''} key={key} onClick={()=>go(key)} aria-current={page===key?'page':undefined}>{label}</button>)}</div>}</section>)}{user.admin&&<button className={`s-nav-group ${page==='admin'?'selected':''}`} title="Administration" onClick={()=>go('admin')}><Icon name="shield"/><span>Administration</span></button>}</nav>
   <div className="s-user"><span className="s-avatar">{user.name.slice(0,2).toUpperCase()}</span><div><strong>{user.name}</strong><small>{user.admin?'Administrateur':'Consultation'}</small></div><button title="Se déconnecter" aria-label="Se déconnecter" onClick={async()=>{try{await api('logout','POST',{});setUser(null);setPage('overview');}catch(e){setError((e as Error).message);}}}><Icon name="logout" size={18}/></button></div>
   <button className="s-collapse" aria-label={compact?'Développer le menu':'Réduire le menu'} onClick={()=>setCompact(c=>{localStorage.setItem('copro-simple-compact',c?'0':'1');return !c;})}>{compact?'›':'‹'}</button>
  </aside>
  <div className="s-content"><header className="s-top"><button className="button secondary s-mobile-menu" onClick={()=>setMobile(true)} aria-label="Ouvrir le menu"><Icon name="menu"/></button><span>{data?.building.name||'Copro.'}<i>/</i>{title}</span><button className="button secondary" onClick={()=>setAccount(true)}><Icon name="shield" size={15}/>Mon compte</button></header>
   <main><div className="s-heading"><p className="eyebrow">LA COPROPRIÉTÉ, ENSEMBLE</p><h1>{title}</h1><p>{descriptions[page]}</p>{!user.admin&&<span className="s-readonly">Consultation · les modifications sont réservées aux administrateurs</span>}</div>
    {error&&<div className="alert" role="alert">{error}<button className="button secondary" onClick={()=>void load()}>Réessayer</button></div>}
    {!data?<p role="status">Chargement des informations…</p>:page==='overview'?<Overview data={data} user={user} go={go}/>:['owners','lots'].includes(page)?<Building key={page} section={page} data={data} admin={user.admin} onChange={load}/>:['banks','charges','funds','payments'].includes(page)?<Finance key={page} section={page} data={data} admin={user.admin} onChange={load} user={user}/>:page==='feed'?<Feed data={data} admin={user.admin}/>:['split','installments','vote'].includes(page)?<div className="s-card s-pad"><Tools key={page} section={page}/></div>:page==='admin'&&user.admin?<Administration data={data} onChange={load}/>:null}
   </main><footer className="s-footer"><span><strong>Copro.</strong> Une gestion plus simple, ensemble.</span><button className="s-version" onClick={()=>setVersion(true)}>Version {__APP_VERSION__}</button></footer>
  </div>
  {account&&<EditForm title="Mon compte" path="password" initial={{current:'',password:''}} fields={[{key:'current',label:'Mot de passe actuel',type:'password',required:true,max:128},{key:'password',label:'Nouveau mot de passe',type:'password',required:true,max:128}]} help={`${user.name} · ${user.admin?'Administrateur':'Lecture seule'}. Utilisez au moins 12 caractères pour votre nouveau mot de passe.`} onClose={()=>setAccount(false)} onDone={()=>setAccount(false)}/>}
  {version&&<Modal title="Mettre à jour l’application" onClose={()=>setVersion(false)}><p className="s-hint">Recharger la dernière version disponible ? Enregistrez d’abord vos modifications en cours.</p><button className="button primary" disabled={updating} onClick={async()=>{setUpdating(true);try{await refreshApplication();}catch(e){setError((e as Error).message);setVersion(false);setUpdating(false);}}}>{updating?'Vérification…':'Recharger la mise à jour'}</button></Modal>}
 </div>;
}
function Login({onLogin,error:initialError}:{onLogin:(user:Row)=>void;error:string}){
 const[username,setUsername]=useState(''),[password,setPassword]=useState(''),[error,setError]=useState(initialError),[busy,setBusy]=useState(false);
 return <div className="login-layout"><section className="login-story"><a className="brand" href="/"><BrandMark/><span>Copro.</span></a><div><p className="eyebrow">VOTRE COPROPRIÉTÉ, ENSEMBLE</p><h1>Un lieu de vie.<br/>Un projet commun.</h1><p>Des comptes clairs.<br/>Des informations partagées.</p><BuildingIllustration/></div><span className="login-footnote">Pensé pour une gestion partagée.</span></section><section className="login-form-side"><form className="login-form" onSubmit={async e=>{e.preventDefault();setBusy(true);setError('');try{const r=await api('login','POST',{username,password});onLogin(r.user);}catch(e){setError((e as Error).message);}finally{setBusy(false);}}}><span className="section-icon"><Icon name="shield" size={24}/></span><p className="eyebrow">BIENVENUE CHEZ VOUS</p><h2>Votre espace copropriété</h2><p className="muted">Les comptes et documents de votre immeuble, au même endroit.</p>{error&&<p className="alert" role="alert">{error}</p>}<label>Courriel ou identifiant<input required type="text" autoComplete="username" autoCapitalize="none" value={username} onChange={e=>setUsername(e.target.value)}/></label><label>Mot de passe<input required type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)}/></label><button className="button primary login-submit" disabled={busy}>{busy?'Connexion…':'Se connecter'}<Icon name="arrow" size={17}/></button><p className="login-help">Chaque copropriétaire dispose de son propre accès.</p></form></section></div>;
}
function Overview({data,user,go}:{data:Row;user:Row;go:(page:string)=>void}){
 const year=today().slice(0,4),paid=data.payments.filter((p:Row)=>p.status==='validated'&&p.owner===user.owner&&p.date.slice(0,4)===year).reduce((s:number,p:Row)=>s+Number(p.amount),0);
 const remaining=data.allocations.filter((a:Row)=>a.owner===user.owner).reduce((s:number,a:Row)=>s+Number(a.remaining),0);
 return <><div className="s-welcome"><div><span className="pill">VOTRE ESPACE COMMUN</span><h2>Moins de démarches.<br/>Plus de clarté.</h2><p>Votre immeuble, ses comptes et les informations utiles.<br/>Tout le monde consulte. Les administrateurs mettent à jour.</p></div><BuildingIllustration/></div><Metrics items={user.owner?[[`Mes paiements en ${year}`,money(paid)],['Mes appels non soldés',money(remaining)],['Lots dans l’immeuble',data.lots.length]]:[['Copropriétaires',data.owners.length],['Lots',data.lots.length],['Solde des comptes',money(data.banks.reduce((s:number,b:Row)=>s+Number(b.balance),0))]]}/><div className="s-grid s-home-grid">{[{page:'owners',icon:'building',title:'Votre immeuble',text:'Copropriétaires, lots et tantièmes.'},{page:'banks',icon:'wallet',title:'Vos finances',text:'Soldes, charges et paiements.'},{page:'feed',icon:'message',title:'La vie de la copropriété',text:'Les nouvelles et documents, classés par sujet.'},{page:'split',icon:'calculator',title:'Vos outils',text:'Des calculs pour préparer vos décisions.'}].map(c=><button key={c.page} className="s-card s-home-card" onClick={()=>go(c.page)}><span className="section-icon"><Icon name={c.icon}/></span><h2>{c.title}</h2><p>{c.text}</p><span className="s-card-link">Consulter <Icon name="arrow" size={16}/></span></button>)}</div>{user.admin&&data.payments.some((p:Row)=>p.status==='pending')&&<div className="s-notice"><div><strong>{data.payments.filter((p:Row)=>p.status==='pending').length} paiement(s) à vérifier</strong><p>Contrôlez les versements reçus avant de mettre les comptes à jour.</p></div><button className="button secondary" onClick={()=>go('payments')}>Vérifier les paiements</button></div>}</>;
}
