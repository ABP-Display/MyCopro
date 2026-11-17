"""Owner cash receipts, permanent-lot attribution and reviewed calls. No data deletion."""
import calendar
from collections import defaultdict
from datetime import date
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_GET
from core.views import manager_required, payload
from core.access import member_required, allow_former_owner
from core.models import Owner, Lot
from governance.models import AssemblyDecision
from .models import (FiscalYear, FundCall, Allocation, Receipt, ReceiptAllocation, BankAccount,
                     Entry, Line, ChargeKey, FinanceProject, AuditEvent, OwnershipChange, Settlement)
from .services import amount, distribute, key_weights, publish_call, open_year, post_entry, bank_for_posting
from .cycle import digest, match_lines, line_remaining
from .forms import CallForm
from .views import errors, call_data
from .idempotency import idempotent

ZERO=Decimal('0')

def calendar_year(params):
    value=int(params.get('year') or timezone.localdate().year)
    if not 1900<=value<=timezone.localdate().year+1:raise ValueError('Année invalide.')
    return value

def receipts(owner=None,year=None):
    q=Receipt.objects.filter(entry__reversal__isnull=True,entry__date__lte=timezone.localdate())
    if owner is not None:q=q.filter(owner=owner)
    if year:q=q.filter(entry__date__year=year)
    return q

def active_links():
    return ReceiptAllocation.objects.filter(settlement__active=True,receipt__entry__reversal__isnull=True)

def liability(allocation):
    transfer=allocation.transfers.filter(mutation__active=True).select_related('mutation','entry').order_by('-mutation__effective_date','-id').first()
    owner=transfer.mutation.new_owner if transfer else allocation.owner
    source=transfer.entry if transfer else allocation.call.entry
    value=allocation.amount
    if transfer:value=source.lines.filter(owner=owner,account__code__startswith='450',debit__gt=0).aggregate(v=Sum('debit'))['v'] or ZERO
    return owner,source,value

def targets(owner):
    rows=[]
    query=Allocation.objects.filter(Q(owner=owner)|Q(transfers__mutation__new_owner=owner),call__entry__isnull=False,call__entry__reversal__isnull=True).distinct().select_related('call','lot','owner')
    for a in query:
        liable,source,value=liability(a)
        if liable.pk!=owner.pk:continue
        debit=source.lines.get(owner=owner,account__code='450',debit__gt=0)
        linked=active_links().filter(allocation=a,receipt__owner=owner).aggregate(v=Sum('amount'))['v'] or ZERO
        available=max(ZERO,min(value-linked,line_remaining(debit)))
        rows.append({'id':a.pk,'call':a.call_id,'label':a.call.label,'lot':a.lot_id,'lot_number':a.lot.number,'due_date':str(a.call.due_date),'amount':str(value),'remaining_for_lot':str(max(ZERO,value-linked)),'available':str(available)})
    return rows

def cash_summary(owner,year):
    from operations.views import owner_balance
    paid=receipts(owner,year).aggregate(v=Sum('amount'))['v'] or ZERO
    years=set(receipts(owner).values_list('entry__date__year',flat=True).distinct())
    years.update(Line.objects.filter(owner=owner,account__code__startswith='450').values_list('entry__date__year',flat=True))
    return {'owner':owner.pk,'name':str(owner),'year':year,'paid':str(paid),
            'paid_total':str(receipts(owner).aggregate(v=Sum('amount'))['v'] or ZERO),
            'balance':str(owner_balance(owner)),'years':sorted(years|{timezone.localdate().year},reverse=True)}

def receipt_data(r):
    links=list(active_links().filter(receipt=r).select_related('allocation__lot','allocation__call'))
    return {'id':r.pk,'owner':r.owner_id,'date':str(r.entry.date),'amount':str(r.amount),'reference':r.entry.reference,
            'unassigned':str(line_remaining(r.entry.lines.get(owner=r.owner,account__code='450',credit__gt=0))),
            'lots':[{'number':a.allocation.lot.number,'call':a.allocation.call.label,'amount':str(a.amount)} for a in links],
            'lot_unassigned':str(r.amount-sum((a.amount for a in links),ZERO))}

@require_GET
@manager_required
@errors
def context(request):
    decisions=[]
    for d in AssemblyDecision.objects.filter(kind='budget',vote__voided_at__isnull=True,vote__workflow__phase__in=['signed','closed']).select_related('vote__workflow__meeting'):
        groups=defaultdict(Decimal)
        for line in d.data.get('lines',[]):groups[int(line['key'])]+=Decimal(str(line['amount']))
        for key,value in groups.items():
            used=FundCall.objects.filter(year_id=d.data['year'],key_id=key,kind='current').filter(Q(entry__isnull=True)|Q(entry__reversal__isnull=True)).aggregate(v=Sum('amount'))['v'] or ZERO
            decisions.append({'id':d.pk,'year':d.data['year'],'key':key,'amount':str(value),'remaining':str(max(ZERO,value-used)),'reference':d.data['reference'],'meeting':d.vote.workflow.meeting.title})
    return JsonResponse({'years':list(FiscalYear.objects.values('id','name','starts_on','ends_on','closed')),
        'owners':[{'id':o.pk,'name':str(o),'email':o.email} for o in Owner.objects.all()],
        'keys':list(ChargeKey.objects.values('id','name','general')),
        'banks':list(BankAccount.objects.filter(active=True).values('id','name','iban','bic','holder','is_default')),
        'projects':list(FinanceProject.objects.filter(completed_on__isnull=True).values('id','name','budget','key_id','decision')),'decisions':decisions})

@require_GET
@manager_required
@errors
def owners(request,pk=None):
    year=calendar_year(request.GET)
    if pk is None:return JsonResponse({'items':[cash_summary(o,year) for o in Owner.objects.all()]})
    o=Owner.objects.get(pk=pk)
    return JsonResponse({'summary':cash_summary(o,year),'receipts':[receipt_data(r) for r in receipts(o,year).select_related('entry','owner').order_by('-entry__date','-id')], 'targets':targets(o)})

@require_GET
@member_required
@allow_former_owner
@errors
def personal(request):
    o=getattr(request.user,'owner_profile',None)
    if not o:return JsonResponse({'error':'Compte copropriétaire requis.'},status=403)
    year=calendar_year(request.GET)
    return JsonResponse({'summary':cash_summary(o,year),'receipts':[receipt_data(r) for r in receipts(o,year).select_related('entry','owner').order_by('-entry__date','-id')],'targets':targets(o)})

def plan(data):
    year=FiscalYear.objects.select_for_update().get(pk=data['year']);key=ChargeKey.objects.select_for_update().get(pk=data['key'])
    if year.closed:raise ValueError('Cet exercice est clôturé.')
    value=amount(data['amount']);count=int(data.get('count',1));interval=int(data.get('interval',3))
    if not 1<=count<=12 or not 1<=interval<=12:raise ValueError('De 1 à 12 échéances espacées de 1 à 12 mois.')
    first=date.fromisoformat(data['first_date']);kind=data.get('kind','current');decision=None
    reference=str(data.get('decision','')).strip()
    if data.get('source_decision'):
        decision=AssemblyDecision.objects.get(pk=data['source_decision'],kind='budget',vote__voided_at__isnull=True,vote__workflow__phase__in=['signed','closed'])
        if kind!='current' or int(decision.data['year'])!=year.pk:raise ValueError('Choisissez l’exercice du budget adopté.')
        ceiling=sum((Decimal(str(r['amount'])) for r in decision.data['lines'] if int(r['key'])==key.pk),ZERO)
        used=FundCall.objects.filter(year=year,key=key,kind='current').filter(Q(entry__isnull=True)|Q(entry__reversal__isnull=True)).aggregate(v=Sum('amount'))['v'] or ZERO
        if value+used>ceiling:raise ValueError('Le montant dépasse le budget voté restant à appeler pour cette répartition.')
        reference=decision.data['reference']
    if not reference or len(reference)>250:raise ValueError('Indiquez la décision d’AG autorisant ces charges.')
    bank=BankAccount.objects.select_related('account').get(pk=data['bank'],active=True,account__active=True)
    if not bank.iban:raise ValueError('Renseignez l’IBAN de la copropriété avant de préparer les avis.')
    if kind not in ['current','works','fund','advance']:raise ValueError('Nature d’appel invalide.')
    project=None
    if kind=='works':
        project=FinanceProject.objects.select_for_update().get(pk=data['project'],key=key,completed_on__isnull=True)
        used=FundCall.objects.filter(project=project,kind='works').filter(Q(entry__isnull=True)|Q(entry__reversal__isnull=True)).aggregate(v=Sum('amount'))['v'] or ZERO
        if used+value>project.budget:raise ValueError('Ce montant dépasse les travaux restant à appeler. Vérifiez les appels déjà préparés depuis l’AG.')
    parts=[]
    for i in range(count):
        y,m=divmod(first.year*12+first.month-1+i*interval,12);due=date(y,m+1,min(first.day,calendar.monthrange(y,m+1)[1]))
        if not year.starts_on<=due<=year.ends_on:raise ValueError('Toutes les échéances doivent appartenir à l’exercice choisi.')
        cents=int(value*100);part=Decimal(cents//count+(i<cents%count))/100
        if part<=0:raise ValueError('Chaque échéance doit être positive.')
        allocations=distribute(part,key_weights(key,due))
        parts.append({'due_date':str(due),'amount':str(part),'rows':[{'lot':l.pk,'number':l.number,'owner':l.owner_id,'name':str(l.owner),'shares':str(w),'amount':str(v)} for l,w,v in allocations]})
    return year,key,bank,decision,reference,project,parts

@require_http_methods(['GET','POST'])
@manager_required
@errors
@idempotent
def charges(request,action=None):
    if request.method=='GET':
        q=FundCall.objects.select_related('key').all()
        if request.GET.get('year'):q=q.filter(year_id=request.GET['year'])
        return JsonResponse({'items':[call_data(c) for c in q]})
    data=payload(request)
    with transaction.atomic():
        year,key,bank,decision,reference,project,parts=plan(data)
        fingerprint=digest({'year':year.pk,'key':key.pk,'bank':bank.pk,'iban':bank.iban,'source':decision.pk if decision else None,'reference':reference,'kind':data.get('kind','current'),'project':project.pk if project else None,'advance_type':data.get('advance_type','reserve'),'label':data.get('label',''),'parts':parts})
        if action=='preview':return JsonResponse({'parts':parts,'preview_hash':fingerprint,'reference':reference})
        if action!='create' or data.get('confirmed') is not True or data.get('preview_hash')!=fingerprint:raise ValueError('Vérifiez un nouvel aperçu avant de confirmer.')
        label=str(data.get('label','')).strip()
        if not label or len(label)>120:raise ValueError('Un libellé de 120 caractères maximum est nécessaire.')
        result=[]
        for i,part in enumerate(parts):
            form=CallForm({'year':year.pk,'key':key.pk,'label':label+(f' {i+1}/{len(parts)}' if len(parts)>1 else ''),'date':part['due_date'],'due_date':part['due_date'],'amount':part['amount'],'kind':data.get('kind','current'),'project':project.pk if project else '', 'decision':reference,'advance_type':data.get('advance_type','reserve')})
            if not form.is_valid():raise ValueError(' · '.join(' '.join(v) for v in form.errors.values()))
            call=form.save(commit=False);call.bank=bank;call.source_decision=decision;call.save()
            if call.date<=timezone.localdate():publish_call(call,request.user)
            result.append({'id':call.pk,'posted':bool(call.entry_id)})
        AuditEvent.objects.create(actor=request.user,action='charges.create',target=','.join(str(r['id']) for r in result))
        return JsonResponse({'items':result},status=201)

def link_receipt(receipt,links,user):
    if not isinstance(links,list) or not 1<=len(links)<=50:raise ValueError('Choisissez de 1 à 50 affectations.')
    if receipt.entry.reversal_of_id or Entry.objects.filter(reversal_of=receipt.entry).exists():raise ValueError('Ce paiement est annulé.')
    credit=receipt.entry.lines.get(owner=receipt.owner,account__code='450',credit__gt=0)
    for row in links:
        allocation=Allocation.objects.select_for_update(of=('self',)).select_related('call','lot','owner').get(pk=row['allocation'],call__entry__isnull=False,call__entry__reversal__isnull=True)
        Lot.objects.select_for_update().get(pk=allocation.lot_id)
        owner,source,value=liability(allocation)
        if owner.pk!=receipt.owner_id:raise ValueError('Cet appel concerne un autre propriétaire. Une dette ne se transfère pas par un paiement.')
        already=active_links().filter(allocation=allocation,receipt__owner=owner).aggregate(v=Sum('amount'))['v'] or ZERO
        portion=amount(row['amount'])
        if portion>value-already:raise ValueError('Ce montant dépasse la part de ce lot restant à affecter.')
        debit=source.lines.get(owner=owner,account__code='450',debit__gt=0)
        remaining=portion
        # Annotate historical matching first, without cancelling or rebooking any money.
        for settled in Settlement.objects.select_for_update().filter(credit_line=credit,debit_line=debit,active=True).order_by('pk'):
            used=active_links().filter(settlement=settled).aggregate(v=Sum('amount'))['v'] or ZERO
            part=min(remaining,settled.amount-used)
            if part>0:
                ReceiptAllocation.objects.create(receipt=receipt,allocation=allocation,settlement=settled,amount=part,created_by=user)
                remaining-=part
            if not remaining:break
        if remaining:
            settled=match_lines(debit,credit,remaining,user)
            ReceiptAllocation.objects.create(receipt=receipt,allocation=allocation,settlement=settled,amount=remaining,created_by=user)
        AuditEvent.objects.create(actor=user,action='receipt.lot',target=str(receipt.pk))

@require_http_methods(['POST'])
@manager_required
@errors
@idempotent
def payment(request):
    data=payload(request)
    if data.get('confirmed') is not True:raise ValueError('Confirmez le règlement réellement reçu et son affectation.')
    with transaction.atomic():
        if data.get('receipt'):
            receipt=Receipt.objects.select_for_update().select_related('entry','owner').get(pk=data['receipt'])
        else:
            day=date.fromisoformat(data['date']);year=open_year(data['year'],day);person=Owner.objects.get(pk=data['owner']);value=amount(data['amount']);bank=bank_for_posting(data.get('bank'));reference=str(data.get('reference','')).strip()
            if len(reference)>100:raise ValueError('Référence de 100 caractères maximum.')
            entry=post_entry(year,day,'BQ','Paiement reçu — '+str(person),[{'code':bank.account.code if bank else '512','debit':value},{'code':'450','owner':person,'credit':value}],request.user,reference)
            receipt=Receipt.objects.create(owner=person,amount=value,entry=entry,bank=bank)
        if data.get('links'):link_receipt(receipt,data['links'],request.user)
        elif data.get('receipt'):raise ValueError('Choisissez un appel et un lot à rattacher.')
        return JsonResponse(receipt_data(receipt),status=201)

@require_GET
@manager_required
@errors
def lot_history(request,pk):
    lot=Lot.objects.get(pk=pk)
    return JsonResponse({'lot':lot.pk,'number':lot.number,'current_owner':str(lot.owner) if lot.owner else 'Non attribué',
        'ownerships':[{'date':str(m.effective_date),'from':str(m.old_owner),'to':str(m.new_owner),'reference':m.reference} for m in lot.ownership_changes.filter(active=True).select_related('old_owner','new_owner')],
        'calls':[{'id':a.pk,'call':a.call.label,'date':str(a.call.due_date),'owner':str(a.owner),'amount':str(a.amount),'cancelled':hasattr(a.call.entry,'reversal')} for a in Allocation.objects.filter(lot=lot).select_related('call__entry','owner')],
        'payments':[{'owner':str(a.receipt.owner),'date':str(a.receipt.entry.date),'amount':str(a.amount),'call':a.allocation.call.label} for a in active_links().filter(allocation__lot=lot).select_related('receipt__entry','receipt__owner','allocation__call')]})
