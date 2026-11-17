"""Editable everyday correspondence; no signature, notification or posting."""
from datetime import date
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from core.models import Owner
from core.views import manager_required, payload
from finance.models import Organization, AuditEvent
from finance.views import errors
from operations.models import Supplier
from .models import Document, Folder
from .views import add_version, validate_upload

CATALOG = [
    {'id':'information','title':'Information aux copropriétaires','description':'Préparer une information sur la vie de l’immeuble, un incident ou une intervention.','target':'owner'},
    {'id':'quote','title':'Demande de devis','description':'Décrire une prestation et reprendre les coordonnées d’un fournisseur.','target':'supplier'},
    {'id':'intervention','title':'Demande d’intervention','description':'Préparer une demande pour une fuite, une panne ou une réparation.','target':'supplier'},
    {'id':'reminder','title':'Point sur un solde débiteur','description':'Préparer un courrier amiable depuis le solde comptable, sans supposer un impayé.','target':'owner'},
]
LIMITS = {'title':150,'recipient':300,'recipient_address':1000,'subject':200,'body':20000,'signature':500}


def definition(key):
    item = next((r for r in CATALOG if r['id']==key),None)
    if not item:
        raise ValueError('Modèle inconnu.')
    return item


def defaults(key, params):
    item = definition(key)
    org = Organization.objects.filter(pk=1).first()
    name = org.name if org else 'Ma copropriété'
    fields = {'title':item['title'],'date':str(timezone.localdate()),
              'recipient':'Les copropriétaires' if item['target']=='owner' else '[À compléter]',
              'recipient_address':'','subject':item['title']+' — '+name,
              'signature':'Le syndic de '+name}
    owner = Owner.objects.get(pk=int(params['owner'])) if params.get('owner') and item['target']=='owner' else None
    supplier = Supplier.objects.get(pk=int(params['supplier']),archived=False) if params.get('supplier') and item['target']=='supplier' else None
    if owner:
        fields['recipient']=str(owner)
        fields['recipient_address']=owner.email
    if supplier:
        fields['recipient']=supplier.name
        fields['recipient_address']='\n'.join(v for v in [supplier.address,supplier.email] if v)
    if key=='information':
        fields['body']='Bonjour,\n\nNous vous informons de la situation suivante :\n[À compléter]\n\nMerci de votre attention.'
    elif key=='quote':
        fields['body']='Bonjour,\n\nNous souhaitons un devis pour la copropriété '+name+'.\n\nPrestation et lieu d’intervention :\n[À compléter]\n\nMerci de préciser votre prix, les prestations comprises, vos disponibilités et la durée de validité du devis. Cette demande ne vaut pas commande.'
    elif key=='intervention':
        fields['body']='Bonjour,\n\nNous vous contactons pour une intervention dans la copropriété '+name+'.\n\nDescription et localisation du problème :\n[À compléter]\n\nMerci de nous indiquer vos disponibilités et les conditions de votre intervention avant tout engagement.'
    else:
        if not owner:
            raise ValueError('Choisissez un copropriétaire pour préparer le point de compte.')
        from operations.views import owner_balance
        from .pdf import money
        balance = owner_balance(owner)
        if balance<=0:
            raise ValueError('Ce compte ne présente pas de solde débiteur à ce jour.')
        fields['body']='Bonjour,\n\nVotre compte présente un solde comptable débiteur de '+money(balance)+' € au '+timezone.localdate().strftime('%d/%m/%Y')+'. Ce solde ne suffit pas à établir un retard : il peut inclure des échéances récentes ou un règlement en cours de traitement.\n\nMerci de nous contacter afin de vérifier ensemble le détail du compte et les paiements effectués.\n\nCe courrier amiable ne constitue pas une mise en demeure.'
    return fields


def validate(data):
    if not isinstance(data,dict) or set(data)-set(LIMITS)-{'date'}:
        raise ValueError('Champs de modèle invalides.')
    fields={}
    for key,limit in LIMITS.items():
        value=data.get(key,'')
        if not isinstance(value,str) or len(value)>limit:
            raise ValueError('Champ '+key+' invalide ou trop long.')
        fields[key]=value.strip()
    fields['date']=str(date.fromisoformat(data.get('date','')))
    if not all(fields[k] for k in ['title','recipient','subject','body','signature']):
        raise ValueError('Complétez le titre, le destinataire, l’objet, le contenu et la signature.')
    if any('[À compléter]' in text for text in fields.values()):
        raise ValueError('Remplacez les mentions [À compléter] avant de créer le document.')
    return fields


def render_letter(fields):
    from .pdf import p, SimpleDocTemplate, A4, Spacer
    org=Organization.objects.filter(pk=1).first()
    stream=BytesIO()
    doc=SimpleDocTemplate(stream,pagesize=A4,leftMargin=42,rightMargin=42,topMargin=42,bottomMargin=48,title=fields['title'],author='Copro.')
    story=[p(org.name if org else 'Copro.','Heading2'),p(org.address if org else ''),
           p(org.email if org else ''),Spacer(1,20),p(fields['recipient'],'Heading3'),
           p(fields['recipient_address']),p('Le '+date.fromisoformat(fields['date']).strftime('%d/%m/%Y')),Spacer(1,15),
           p(fields['subject'],'Heading2'),Spacer(1,10),p(fields['body']),Spacer(1,22),p(fields['signature'])]
    def footer(canvas,document):
        canvas.setFont('Copro',7)
        canvas.drawString(42,24,'Copro. · Courrier préparé, non signé et non envoyé · Page '+str(document.page))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return stream.getvalue()


@require_http_methods(['GET'])
@manager_required
@errors
def catalog(request):
    return JsonResponse({'items':CATALOG,
        'owners':[{'id':o.pk,'name':str(o)} for o in Owner.objects.all()],
        'suppliers':list(Supplier.objects.filter(archived=False).values('id','name'))})


@require_http_methods(['GET','POST'])
@manager_required
@errors
def prepare(request,key):
    definition(key)
    if request.method=='GET':
        return JsonResponse({'fields':defaults(key,request.GET)})
    data=payload(request)
    if data.get('reviewed') is not True:
        raise ValueError('Relisez le document et confirmez sa création.')
    fields=validate(data.get('fields'))
    content=render_letter(fields)
    file=SimpleUploadedFile('modele-'+key+'.pdf',content,content_type='application/pdf')
    info=validate_upload(file)
    version=None
    try:
        with transaction.atomic():
            folder,_=Folder.objects.get_or_create(name='Courriers préparés')
            document=Document.objects.create(title=fields['title'],folder=folder,published=False)
            version=add_version(document,file,info,request.user)
            AuditEvent.objects.create(actor=request.user,action='document.template.create',target=key+':'+str(document.pk))
    except Exception:
        if version:version.file.delete(save=False)
        raise
    return JsonResponse({'id':document.pk,'title':document.title,'download':'/api/documents/items/'+str(document.pk)+'/download/'},status=201)
