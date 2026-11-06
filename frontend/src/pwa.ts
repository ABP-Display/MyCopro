let registration:Promise<ServiceWorkerRegistration>|undefined;
export function registerAppWorker(){
  if(import.meta.env.PROD&&'serviceWorker' in navigator&&window.isSecureContext){
    registration??=navigator.serviceWorker.register('/sw.js',{scope:'/',updateViaCache:'none'});
    void registration.catch(()=>{});
  }
  return registration;
}
function installed(worker:ServiceWorker){return new Promise<void>((resolve,reject)=>{
  const timer=window.setTimeout(()=>{cleanup();reject(new Error('La mise à jour prend trop de temps. Réessayez dans un instant.'));},15000);
  const cleanup=()=>{clearTimeout(timer);worker.removeEventListener('statechange',change);};
  const change=()=>{if(['installed','activated'].includes(worker.state)){cleanup();resolve();}else if(worker.state==='redundant'){cleanup();reject(new Error('La mise à jour n’a pas pu être installée. Réessayez.'));}};
  worker.addEventListener('statechange',change);change();
});}
export async function refreshApplication(){
  // Check connectivity before discarding any screen. Never clear cookies or private storage.
  const response=await fetch('/version.json',{cache:'no-store',signal:AbortSignal.timeout(10000)});
  if(!response.ok)throw new Error('La version du serveur est indisponible. Réessayez plus tard.');
  const metadata=await response.json();
  if(!/^\d{4}\.\d{2}\.\d{2}\.\d{4}$/.test(metadata.version))throw new Error('La version du serveur n’est pas reconnue.');
  const reg=await registerAppWorker();
  if(reg){await reg.update();if(reg.installing)await installed(reg.installing);
    if(reg.waiting){const worker=reg.waiting;await new Promise<void>((resolve,reject)=>{
      const timer=setTimeout(()=>{cleanup();reject(new Error('L’activation a échoué. Réessayez.'));},15000);
      const cleanup=()=>{clearTimeout(timer);worker.removeEventListener('statechange',change);};
      const change=()=>{if(worker.state==='activated'){cleanup();resolve();}else if(worker.state==='redundant'){cleanup();reject(new Error('La mise à jour est indisponible.'));}};
      worker.addEventListener('statechange',change);worker.postMessage({type:'APPLY_UPDATE'});change();
    });}
  }
  window.location.reload();
}
