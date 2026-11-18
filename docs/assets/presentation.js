// Navigation enhancement only: the presentation also works without JavaScript.
const menu=document.querySelector('.mobile-nav');
menu?.querySelectorAll('a').forEach(link=>link.addEventListener('click',()=>{menu.open=false;}));
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&menu?.open){menu.open=false;menu.querySelector('summary').focus();}});
