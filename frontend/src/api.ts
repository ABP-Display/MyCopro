let csrf='';
export function newOperationId(){if(crypto.randomUUID)return crypto.randomUUID();const bytes=crypto.getRandomValues(new Uint8Array(16));bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;const hex=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;}
export async function api<T=Record<string,any>>(path:string,method='GET',body?:unknown):Promise<T>{
  const form=body instanceof FormData;
  const [route,query]=path.split('?');
  const response=await fetch(`/api/${route.replace(/\/$/,'')}/${query?`?${query}`:''}`,{
    method,credentials:'same-origin',cache:'no-store',
    headers:{...(form?{}:{'Content-Type':'application/json'}),...(method==='GET'?{}:{'X-CSRFToken':csrf})},
    body:body===undefined?undefined:form?body as FormData:JSON.stringify(body),
  });
  if(!response.headers.get('content-type')?.includes('application/json')){
    throw new Error(response.status===413?'La publication dépasse la limite de 12 Mo. Réduisez les pièces jointes.':'Le serveur est momentanément indisponible. Réessayez.');
  }
  const value=await response.json();
  if(response.status===401&&!route.startsWith('login'))window.dispatchEvent(new Event('copro:reauthenticate'));
  if(value.archived_access)window.dispatchEvent(new Event('copro:archive'));
  if(value.csrf)csrf=value.csrf;
  if(!response.ok)throw new Error(value.error||'La demande a échoué. Réessayez.');
  return value;
}
