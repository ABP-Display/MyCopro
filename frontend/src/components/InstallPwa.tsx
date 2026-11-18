import {useEffect,useState} from 'react';
import {Modal} from './Common';
import {Icon} from './ui';
import './install-pwa.css';

type InstallPrompt=Event&{
  prompt:()=>Promise<{outcome:'accepted'|'dismissed'}|void>;
  userChoice?:Promise<{outcome:'accepted'|'dismissed'}>;
};
let pending:InstallPrompt|null=null;
let installed=false;
const notify=()=>window.dispatchEvent(new Event('copro:install-state'));
// Capture eligibility even when the user has not logged in yet.
window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();pending=event as InstallPrompt;notify();});
window.addEventListener('appinstalled',()=>{installed=true;pending=null;notify();});
const standalone=()=>installed||matchMedia('(display-mode: standalone)').matches||!!(navigator as Navigator&{standalone?:boolean}).standalone;

export function InstallPwa(){
 const[isInstalled,setInstalled]=useState(standalone),[ready,setReady]=useState(()=>!!pending),[help,setHelp]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('');
 useEffect(()=>{const display=matchMedia('(display-mode: standalone)');const update=()=>{const done=standalone();setInstalled(done);setReady(!!pending);if(done)setHelp(false);};update();window.addEventListener('copro:install-state',update);display.addEventListener('change',update);return()=>{window.removeEventListener('copro:install-state',update);display.removeEventListener('change',update);};},[]);
 async function install(){
  if(busy)return;
  if(!pending){setHelp(true);return;}
  const invitation=pending;pending=null;notify();setBusy(true);setError('');
  try{await invitation.prompt();if(invitation.userChoice)await invitation.userChoice;setHelp(false);}
  catch{setError('La fenêtre d’installation n’a pas pu s’ouvrir. Utilisez le menu de votre navigateur.');setHelp(true);}
  finally{setBusy(false);}
 }
 if(isInstalled)return null;
 const apple=/iPhone|iPad|iPod/i.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
 return <>
  <button type="button" className="button secondary s-pwa-install" title="Installer l’application" aria-label="Installer l’application" disabled={busy} onClick={()=>void install()}><Icon name="download" size={19}/></button>
  {help&&<Modal title="Installer Copro." busy={busy} onClose={()=>setHelp(false)}><div className="install-heading"><span className="account-emblem"><Icon name="download" size={26}/></span><div><h3>Copro. à portée de main</h3><p>Ajoutez l’application à votre écran d’accueil ou à votre ordinateur.</p></div></div>{error&&<p className="alert" role="alert">{error}</p>}{!window.isSecureContext?<p className="install-note">Ouvrez le site avec son adresse HTTPS pour pouvoir installer l’application. L’installation depuis une adresse IP locale en HTTP n’est pas disponible.</p>:apple?<ol className="install-steps"><li>Ouvrez cette page dans <strong>Safari</strong>.</li><li>Ouvrez le menu <strong>Partager</strong>.</li><li>Choisissez <strong>Sur l’écran d’accueil</strong>, puis confirmez avec <strong>Ajouter</strong>.</li></ol>:<ol className="install-steps"><li>Ouvrez le menu de votre navigateur ou l’icône d’installation dans la barre d’adresse.</li><li>Choisissez <strong>Installer l’application</strong> ou <strong>Ajouter à l’écran d’accueil</strong>, selon votre navigateur.</li><li>Confirmez pour retrouver Copro. parmi vos applications. Si l’option n’apparaît pas, essayez depuis Chrome ou Edge.</li></ol>}<p className="install-note">Vous utiliserez les mêmes identifiants. Une connexion au serveur reste nécessaire pour consulter les données.</p>{ready&&<div className="install-actions"><button className="button primary" disabled={busy} onClick={()=>void install()}><Icon name="download" size={17}/>Installer maintenant</button></div>}</Modal>}
 </>;
}
