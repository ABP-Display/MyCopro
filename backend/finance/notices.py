"""Immutable, private PDF editions; email is prepared in the user's own mail client."""
from decimal import Decimal
from io import BytesIO
from django.db import transaction
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import JsonResponse,FileResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods,require_GET
from core.views import manager_required,payload
from core.access import member_required,allow_former_owner,is_manager
from core.models import Owner
from documents.models import Document
from documents.views import validate_upload,add_version
from .models import FundCall,CallNotice,Organization,BankAccount,AuditEvent
from .residents import liability
from .cycle import digest
from .views import errors

def notice_data(notice):
    return {'id':notice.pk,'call':notice.call_id,'owner':notice.owner_id,'name':notice.snapshot['owner']['name'],
            'email':notice.snapshot['owner']['email'],'amount':notice.snapshot['amount'],'label':notice.snapshot['label'],
            'due_date':notice.snapshot['due_date'],'reference':notice.snapshot['reference'],'iban':notice.snapshot['bank']['iban'],
            'created_at':notice.created_at,'cancelled':hasattr(notice.call.entry,'reversal')}

def snapshot(call,owner,bank):
    rows=[]
    for allocation in call.allocations.select_related('lot','owner'):
        liable,source,value=liability(allocation)
        if liable.pk==owner.pk and value>0:rows.append({'lot':allocation.lot_id,'number':allocation.lot.number,'shares':str(allocation.shares),'amount':str(value),'transferred':source.pk!=call.entry_id})
    if not rows:raise ValueError('Cet appel ne concerne pas ce copropriétaire.')
    org=Organization.objects.filter(pk=1).first()
    return {'organization':{'name':org.name if org else 'Copro.','address':org.address if org else ''},
        'owner':{'id':owner.pk,'name':str(owner),'email':owner.email},'rows':rows,'amount':str(sum((Decimal(r['amount']) for r in rows),Decimal(0))),
        'total_shares':str(sum((a.shares for a in call.allocations.all()),Decimal(0))),'label':call.label,'date':str(call.date),'due_date':str(call.due_date),'decision':call.decision,
        'reference':f'COPRO-{call.pk}-{owner.pk}','key':call.key.name,
        'bank':{'holder':bank.holder or (org.name if org else ''),'name':bank.bank_name or bank.name,'iban':bank.iban,'bic':bank.bic}}

def render_notice(data):
    from documents.pdf import p,table,money,SimpleDocTemplate,A4,Spacer
    stream=BytesIO();width=A4[0]-80
    doc=SimpleDocTemplate(stream,pagesize=A4,leftMargin=40,rightMargin=40,topMargin=35,bottomMargin=45,title='Avis individuel d’appel de charges',author='Copro.')
    bank=data['bank'];story=[p(data['organization']['name'],'Heading2'),p(data['organization']['address']),Spacer(1,10),
        p('Votre appel de charges','Heading1'),p(data['owner']['name'],'Heading2'),p(data['owner']['email']),p(data['label']),
        p('Date de l’appel : '+data['date']+' · À payer au plus tard le '+data['due_date']),
        p('Répartition : '+data['key']),p('Décision : '+data['decision']),Spacer(1,12),
        table(['Lot','Tantièmes retenus','Votre part (€)'],[[r['number']+(' — part réattribuée' if r.get('transferred') else ''),r['shares']+(' / '+data['total_shares'] if data.get('total_shares') else ''),money(r['amount'])] for r in data['rows']],[width*.25,width*.35,width*.40],(1,2)),
        Spacer(1,14),p('Montant de cet avis : '+money(data['amount'])+' €','Heading2'),
        p('Coordonnées pour votre virement','Heading2'),p('Titulaire : '+bank['holder']),p('Banque : '+bank['name']),
        p('IBAN : '+' '.join(bank['iban'][i:i+4] for i in range(0,len(bank['iban']),4))),p('BIC : '+(bank['bic'] or 'Non renseigné')),
        p('Référence à indiquer : '+data['reference']),Spacer(1,12),
        p('Les paiements déjà effectués et votre solde cumulé sont visibles dans votre espace personnel. Cet avis décrit le montant appelé, il ne constitue pas une relance ni la preuve d’un retard. Ne payez pas une seconde fois une somme déjà réglée.')]
    def footer(canvas,document):
        canvas.setFont('Copro',8);canvas.drawString(40,23,'Copro. · Avis personnel · '+data['reference']+' · Page '+str(document.page))
    doc.build(story,onFirstPage=footer,onLaterPages=footer);return stream.getvalue()

@require_http_methods(['GET','POST'])
@manager_required
@errors
def call_notices(request,pk):
    call=FundCall.objects.select_related('bank','key','entry').get(pk=pk)
    if request.method=='GET':return JsonResponse({'items':[notice_data(n) for n in call.notices.select_related('call__entry').order_by('-id')]})
    if payload(request).get('confirmed') is not True:raise ValueError('Confirmez la préparation des avis PDF. Aucun e-mail ne sera envoyé automatiquement.')
    created_files=[]
    try:
        with transaction.atomic():
            call=FundCall.objects.select_for_update(of=('self',)).select_related('key','entry','bank').get(pk=pk,entry__isnull=False,entry__reversal__isnull=True)
            bank=call.bank or BankAccount.objects.filter(is_default=True,active=True).first()
            if not bank or not bank.iban:raise ValueError('Renseignez un compte bancaire et son IBAN avant de générer les avis.')
            owner_ids={liability(a)[0].pk for a in call.allocations.select_related('owner','call')}
            if len(owner_ids)>200:raise ValueError('Préparez les avis par groupes pour une copropriété de plus de 200 destinataires.')
            result=[]
            for owner in Owner.objects.filter(pk__in=owner_ids):
                data=snapshot(call,owner,bank);fingerprint=digest(data)
                existing=CallNotice.objects.filter(call=call,owner=owner,source_hash=fingerprint).first()
                if existing:result.append(notice_data(existing));continue
                content=SimpleUploadedFile(f'avis-{call.pk}-{owner.pk}.pdf',render_notice(data),content_type='application/pdf')
                document=Document.objects.create(title=(f'Avis {call.pk} — {owner}')[:150],published=False)
                version=add_version(document,content,validate_upload(content),request.user);created_files.append(version.file)
                notice=CallNotice.objects.create(call=call,owner=owner,version=version,snapshot=data,source_hash=fingerprint,created_by=request.user)
                result.append(notice_data(notice))
            AuditEvent.objects.create(actor=request.user,action='notices.prepare',target=str(call.pk))
            return JsonResponse({'items':result},status=201)
    except Exception:
        for file in created_files:file.delete(save=False)
        raise

@require_GET
@member_required
@allow_former_owner
@errors
def my_notices(request):
    owner=getattr(request.user,'owner_profile',None)
    if not owner:return JsonResponse({'error':'Compte copropriétaire requis.'},status=403)
    q=CallNotice.objects.filter(owner=owner).select_related('call__entry').order_by('-created_at')
    if request.GET.get('year'):q=q.filter(call__due_date__year=int(request.GET['year']))
    return JsonResponse({'items':[notice_data(n) for n in q]})

@require_GET
@member_required
@allow_former_owner
@errors
def download(request,pk):
    q=CallNotice.objects.select_related('version')
    if not is_manager(request.user):q=q.filter(owner__user=request.user)
    n=q.get(pk=pk)
    response=FileResponse(n.version.file.open('rb'),content_type='application/pdf',as_attachment=True,filename=f'avis-{n.call_id}-{n.owner_id}.pdf')
    response['Cache-Control']='private, no-store';response['X-Content-Type-Options']='nosniff'
    return response
