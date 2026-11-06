import type { Plugin } from 'vite';

export function appVersion(date = new Date()) {
  const parts = new Intl.DateTimeFormat('en-GB', {timeZone:'Europe/Paris',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(date);
  const get=(key:string)=>parts.find(p=>p.type===key)!.value;
  return `${get('year')}.${get('month')}.${get('day')}.${get('hour')}${get('minute')}`;
}

export function pwaPlugin(version:string):Plugin {
  const buildId=Date.now().toString(36);
  return {name:'copro-pwa',generateBundle(_,bundle){
    const files=['/offline.html','/offline.css','/copro-mark.svg','/icons/icon-192.png','/icons/icon-512.png','/icons/maskable-512.png','/icons/apple-touch-icon.png',...Object.keys(bundle).filter(p=>p.startsWith('assets/')&&!p.endsWith('.map')).map(p=>'/'+p)];
    this.emitFile({type:'asset',fileName:'version.json',source:JSON.stringify({version,buildId})});
    this.emitFile({type:'asset',fileName:'sw.js',source:`
const CACHE='copro-static-${buildId}';
const FILES=${JSON.stringify(files)};
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(FILES))));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('copro-static-')).slice(0,-3).map(k=>caches.delete(k))))));
self.addEventListener('message',event=>{if(event.data?.type==='APPLY_UPDATE')self.skipWaiting();});
self.addEventListener('fetch',event=>{
  const req=event.request,url=new URL(req.url);
  if(req.method!=='GET'||url.origin!==self.location.origin||url.pathname.startsWith('/api/'))return;
  if(req.mode==='navigate'){
    event.respondWith(fetch(req).catch(()=>caches.open(CACHE).then(cache=>cache.match('/offline.html'))));return;
  }
  if(FILES.includes(url.pathname)||url.pathname.startsWith('/assets/')){
    event.respondWith(caches.keys().then(async keys=>{
      for(const key of keys.filter(k=>k.startsWith('copro-static-')).reverse()){
        const found=await (await caches.open(key)).match(req);if(found)return found;
      }
      return fetch(req);
    }));
  }
});
`});
  }};
}
