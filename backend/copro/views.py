import calendar
import hashlib
import json
import re
import uuid
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from functools import wraps
from pathlib import Path

from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout, get_user_model, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.validators import validate_email
from django.db import transaction, IntegrityError
from django.db.models import Sum
from django.http import JsonResponse, FileResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from .models import Building, Owner, Lot, Ownership, Bank, Call, Allocation, Payment, Category, Post, Attachment, Movement, Operation, Audit, LoginAttempt


def csrf_failure(request, reason=''):
    return JsonResponse({'error':'Session expirée. Rechargez la page avant de réessayer.'}, status=403)


def user_data(user):
    from .security import status
    owner = Owner.objects.filter(user=user).first()
    return {'id':user.pk, 'name':str(owner) if owner else user.get_full_name() or user.username,
            'admin':user.is_staff or user.is_superuser, 'owner':owner.pk if owner else None, **status(user)}


def guarded(admin=False, methods=('GET',), readonly=False):
    def decorate(fn):
        @wraps(fn)
        @require_http_methods(methods)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error':'Connexion nécessaire.'}, status=401)
            if (admin or request.method != 'GET' and not readonly) and not (request.user.is_staff or request.user.is_superuser):
                return JsonResponse({'error':'Action réservée aux administrateurs.'}, status=403)
            try:
                return fn(request, *args, **kwargs)
            except ObjectDoesNotExist:
                return JsonResponse({'error':'Élément introuvable.'}, status=404)
            except (ValueError, KeyError, TypeError, InvalidOperation, ValidationError) as error:
                message = ' · '.join(error.messages) if isinstance(error, ValidationError) else str(error)
                return JsonResponse({'error':message or 'Données invalides.'}, status=400)
            except IntegrityError:
                return JsonResponse({'error':'Cette référence ou ce courriel existe déjà.'}, status=409)
        return wrapped
    return decorate


def payload(request):
    data = json.loads(request.body or '{}')
    if not isinstance(data, dict):
        raise ValueError('Objet JSON attendu.')
    return data


def text(data, key, maximum=150, required=True):
    value = data.get(key, '')
    if not isinstance(value, str):
        raise ValueError(f'{key} : texte attendu.')
    value = value.strip()
    if (required and not value) or len(value) > maximum:
        raise ValueError(f'{key} : renseignez une valeur de {maximum} caractères maximum.')
    return value


def money(value, positive=False):
    result = Decimal(str(value))
    if not result.is_finite() or abs(result) > Decimal('9999999999.99') or result != result.quantize(Decimal('.01')):
        raise ValueError('Montant invalide : deux décimales maximum.')
    if positive and result <= 0:
        raise ValueError('Un montant strictement positif est nécessaire.')
    return result


def day(value):
    result = date.fromisoformat(str(value))
    if not 1900 <= result.year <= 2200:
        raise ValueError('Date hors limites.')
    return result


def boolean(data, key, default=False):
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f'{key} : choix invalide.')
    return value


def transact(request, data, action):
    token = uuid.UUID(str(data['request_id']))
    fingerprint = hashlib.sha256(json.dumps([request.path, request.user.pk, data],sort_keys=True).encode()).hexdigest()
    with transaction.atomic():
        Building.objects.get_or_create(pk=1)
        Building.objects.select_for_update().get(pk=1)
        previous = Operation.objects.filter(token=token).first()
        if previous:
            if previous.fingerprint != fingerprint:
                raise ValueError('Cette opération a déjà été utilisée avec d’autres données.')
            return JsonResponse(previous.response)
        response = action()
        Operation.objects.create(token=token,fingerprint=fingerprint,response=response)
        Audit.objects.create(actor=request.user,action=request.path[:100],target=str(response.get('id','')))
        return JsonResponse(response)


@ensure_csrf_cookie
@require_http_methods(['GET'])
def session(request):
    return JsonResponse({'user':user_data(request.user) if request.user.is_authenticated else None, 'csrf':get_token(request)})


@require_http_methods(['POST'])
def login(request):
    try:
        data = payload(request)
        username = text(data,'username',254)
        username=username.lower() if '@' in username else username
        key=hashlib.sha256(username.casefold().encode()).hexdigest()
        with transaction.atomic():
            Building.objects.get_or_create(pk=1)
            Building.objects.select_for_update().get(pk=1)
            attempt,_=LoginAttempt.objects.get_or_create(key=key,defaults={'since':timezone.now()})
            if attempt.since < timezone.now()-timedelta(minutes=15):
                attempt.count=0;attempt.since=timezone.now()
            if attempt.count>=10:
                return JsonResponse({'error':'Trop de tentatives. Réessayez dans 15 minutes.'},status=429)
            user = authenticate(request,username=username,password=data.get('password',''))
            attempt.count=0 if user else attempt.count+1
            attempt.save()
        if user is None:
            return JsonResponse({'error':'Identifiant ou mot de passe incorrect.'},status=401)
        from .security import begin_login
        challenge=begin_login(request,user)
        if challenge is not None:return challenge
        auth_login(request,user)
        return JsonResponse({'user':user_data(user),'csrf':get_token(request)})
    except (ValueError, TypeError, KeyError):
        return JsonResponse({'error':'Données de connexion invalides.'},status=400)


@require_http_methods(['POST'])
def logout(request):
    auth_logout(request)
    return JsonResponse({'ok':True})


@require_http_methods(['POST'])
def password(request):
    from .security import change_password
    return change_password(request)


def bank_data(bank):
    net=bank.movements.aggregate(total=Sum('amount'))['total'] or Decimal(0)
    return {'id':bank.pk,'name':bank.name,'institution':bank.institution,'holder':bank.holder,'iban':bank.iban,'bic':bank.bic,
            'opening_balance':str(bank.opening_balance),'opened_on':str(bank.opened_on),'active':bank.active,
            'balance':str(bank.opening_balance+net)}


def allocation_data(item):
    paid = item.payment_set.filter(status='validated').aggregate(total=Sum('amount'))['total'] or Decimal(0)
    return {'id':item.pk,'call':item.call_id,'label':item.call.label,'kind':item.call.kind,'due_date':str(item.call.due_date),
            'lot':item.lot_id,'number':item.lot.number,'owner':item.owner_id,'name':str(item.owner),
            'shares':str(item.shares),'amount':str(item.amount),'paid':str(paid),'remaining':str(item.amount-paid),'bank':item.call.bank_id}


@guarded()
def state(request):
    building,_=Building.objects.get_or_create(pk=1)
    owners=[{'id':o.pk,'first_name':o.first_name,'last_name':o.last_name,'name':str(o),'email':o.email,'phone':o.phone,
             'active':o.active,'admin':bool(o.user_id and o.user.is_staff),'has_access':bool(o.user_id)} for o in Owner.objects.select_related('user')]
    lots=list(Lot.objects.values('id','number','description','shares','owner'))
    banks=[bank_data(b) for b in Bank.objects.all()]
    allocations=[allocation_data(a) for a in Allocation.objects.select_related('call','lot','owner')]
    payments=[{'id':p.pk,'owner':p.owner_id,'name':str(p.owner),'lot':p.lot_id,'number':p.lot.number if p.lot_id else '',
               'allocation':p.allocation_id,'bank':p.bank_id,'amount':str(p.amount),'date':str(p.date),'status':p.status,
               'reference':p.reference} for p in Payment.objects.select_related('owner','lot')]
    calls=[{'id':c.pk,'label':c.label,'kind':c.kind,'decision':c.decision,'amount':str(c.amount),'due_date':str(c.due_date),
            'bank':c.bank_id} for c in Call.objects.all()]
    movements=[{'id':m.pk,'bank':m.bank_id,'date':str(m.date),'label':m.label,'reference':m.reference,'amount':str(m.amount),
                'kind':m.kind,'payment':m.payment_id,'document':m.document_id} for m in Movement.objects.all()]
    return JsonResponse({'building':{'name':building.name,'address':building.address},'owners':owners,'lots':lots,
                         'banks':banks,'allocations':allocations,'payments':payments,'calls':calls,'movements':movements,
                         'categories':list(Category.objects.values('id','name','active'))})


@guarded(admin=True,methods=('POST',))
def owners(request, pk=None):
    data=payload(request)
    def action():
        item=Owner.objects.get(pk=pk) if pk else Owner()
        item.first_name=text(data,'first_name',100);item.last_name=text(data,'last_name',100)
        item.email=text(data,'email',254).lower();validate_email(item.email)
        item.phone=text(data,'phone',30,False);item.active=boolean(data,'active',True)
        if Owner.objects.exclude(pk=pk).filter(email__iexact=item.email).exists():
            raise ValueError('Ce courriel est déjà utilisé.')
        chosen=text(data,'password',128,False)
        if not item.user_id and not chosen:
            raise ValueError('Choisissez un mot de passe initial pour créer son accès.')
        user=item.user if item.user_id else get_user_model()()
        user.username=item.email;user.email=item.email;user.first_name=item.first_name;user.last_name=item.last_name;user.is_active=item.active
        if chosen:
            validate_password(chosen,user);user.set_password(chosen)
        user.save();item.user=user;item.save()
        return {'id':item.pk}
    return transact(request,data,action)


@guarded(admin=True,methods=('POST',))
def lots(request,pk=None):
    data=payload(request)
    def action():
        item=Lot.objects.get(pk=pk) if pk else Lot()
        previous=item.owner_id
        item.number=text(data,'number',30);item.description=text(data,'description',200,False)
        item.shares=money(data['shares'],True)
        item.owner=Owner.objects.get(pk=data['owner'],active=True) if data.get('owner') else None
        if previous != item.owner_id and pk:
            Ownership.objects.create(lot=item,previous_id=previous,owner=item.owner,date=timezone.localdate(),actor=request.user)
        item.save()
        return {'id':item.pk}
    return transact(request,data,action)


@guarded(admin=True,methods=('POST',))
def banks(request,pk=None):
    data=payload(request)
    def action():
        item=Bank.objects.get(pk=pk) if pk else Bank()
        value=money(data.get('opening_balance',0));opened=day(data['opened_on'])
        if pk and (item.opening_balance != value or item.opened_on != opened):
            raise ValueError('Le solde et la date de départ sont conservés. Les opérations font évoluer le compte.')
        if opened > timezone.localdate():
            raise ValueError('La date de départ ne peut pas être future.')
        item.name=text(data,'name');item.institution=text(data,'institution',150,False);item.holder=text(data,'holder')
        item.iban=''.join(text(data,'iban',64,False).split()).upper()
        if item.iban and (not re.fullmatch(r'[A-Z]{2}\d{2}[A-Z0-9]{11,30}',item.iban) or len(item.iban)>34):
            raise ValueError('Format IBAN invalide.')
        item.bic=text(data,'bic',11,False).upper()
        if item.bic and not re.fullmatch(r'[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?',item.bic):
            raise ValueError('BIC invalide.')
        item.opening_balance=value;item.opened_on=opened;item.active=boolean(data,'active',True);item.save()
        return {'id':item.pk}
    return transact(request,data,action)


def distribute(total, weights):
    cents=int(money(total,True)*100)
    denominator=sum(weights,Decimal(0))
    if not weights or denominator<=0:
        raise ValueError('Renseignez des tantièmes positifs pour vos lots.')
    exact=[Decimal(cents)*w/denominator for w in weights]
    parts=[int(v.to_integral_value(rounding=ROUND_DOWN)) for v in exact]
    order=sorted(range(len(parts)),key=lambda i:exact[i]-parts[i],reverse=True)
    for i in order[:cents-sum(parts)]:parts[i]+=1
    return [Decimal(v)/100 for v in parts]


def charge_preview(data):
    bank=Bank.objects.get(pk=data['bank'],active=True)
    label=text(data,'label');decision=text(data,'decision',250)
    kind=data['kind']
    if kind not in ('charges','works','exceptional'):raise ValueError('Type d’appel invalide.')
    count=int(data.get('count',1));interval=int(data.get('interval',3));first=day(data['due_date'])
    if not 1<=count<=12 or interval not in (1,3,6,12):raise ValueError('Échéancier invalide.')
    lots=list(Lot.objects.select_related('owner').all())
    if not lots or any(not l.owner_id or not l.owner.active for l in lots):
        raise ValueError('Chaque lot doit avoir un propriétaire actif avant de répartir les charges.')
    amounts=distribute(data['amount'],[Decimal(1)]*count)
    parts=[]
    for n,total in enumerate(amounts):
        offset=first.year*12+first.month-1+n*interval
        year,month=divmod(offset,12);month+=1
        due=day(date(year,month,min(first.day,calendar.monthrange(year,month)[1])))
        values=distribute(total,[l.shares for l in lots])
        parts.append({'date':str(due),'amount':str(total),'rows':[{'lot':l.pk,'number':l.number,'owner':l.owner_id,'name':str(l.owner),'shares':str(l.shares),'amount':str(value)} for l,value in zip(lots,values)]})
    result={'label':label,'decision':decision,'kind':kind,'bank':bank.pk,'parts':parts}
    result['hash']=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
    return result


@guarded(admin=True,methods=('POST',))
def calls(request,action):
    data=payload(request)
    if action=='preview':return JsonResponse(charge_preview(data))
    if action!='create':raise ValueError('Action inconnue.')
    def create():
        preview=charge_preview(data)
        if preview['hash'] != data.get('hash'):raise ValueError('La répartition a changé. Recalculez l’aperçu.')
        ids=[]
        for part in preview['parts']:
            call=Call.objects.create(label=preview['label'],kind=preview['kind'],decision=preview['decision'],
                                     due_date=part['date'],amount=part['amount'],bank_id=preview['bank'])
            Allocation.objects.bulk_create([Allocation(call=call,lot_id=r['lot'],owner_id=r['owner'],shares=r['shares'],amount=r['amount']) for r in part['rows']])
            ids.append(call.pk)
        return {'ids':ids}
    return transact(request,data,create)


def validate_payment(item,user):
    if item.status!='pending':raise ValueError('Ce paiement a déjà été traité.')
    if item.allocation_id:
        allocated=allocation_data(item.allocation)
        if item.amount>Decimal(allocated['remaining']):raise ValueError('Le paiement dépasse le reste à payer sur cet appel/lot. Répartissez le versement.')
    if not item.bank.active:raise ValueError('Ce compte bancaire est inactif.')
    Movement.objects.create(bank=item.bank,date=item.date,label=f'Paiement · {item.owner}',reference=item.reference,
                            amount=item.amount,payment=item,kind='payment',actor=user)
    item.status='validated';item.validated_by=user;item.validated_at=timezone.now();item.save()


@guarded(admin=True,methods=('POST',))
def payments(request,pk=None,action=None):
    data=payload(request)
    def save():
        if pk:
            item=Payment.objects.select_related('bank','owner','allocation__call','allocation__lot','allocation__owner').get(pk=pk)
            if action=='validate':validate_payment(item,request.user)
            elif action=='reject' and item.status=='pending':
                item.status='rejected';item.save(update_fields=['status'])
            else:raise ValueError('Action impossible pour ce paiement.')
        else:
            owner=Owner.objects.get(pk=data['owner'])
            bank=Bank.objects.get(pk=data['bank'],active=True)
            paid_on=day(data['date'])
            if paid_on>timezone.localdate() or paid_on<bank.opened_on:raise ValueError('La date doit être comprise entre l’ouverture du compte et aujourd’hui.')
            allocation=Allocation.objects.select_related('call','lot','owner').get(pk=data['allocation']) if data.get('allocation') else None
            lot=allocation.lot if allocation else (Lot.objects.get(pk=data['lot']) if data.get('lot') else None)
            if allocation and allocation.owner_id!=owner.pk:raise ValueError('Cet appel appartient à un autre copropriétaire.')
            if lot and not allocation and lot.owner_id!=owner.pk:raise ValueError('Ce lot appartient à un autre copropriétaire. Choisissez un appel historique si nécessaire.')
            item=Payment.objects.create(owner=owner,bank=bank,lot=lot,allocation=allocation,amount=money(data['amount'],True),date=paid_on,reference=text(data,'reference',150,False))
            if boolean(data,'validate'):validate_payment(item,request.user)
        return {'id':item.pk}
    return transact(request,data,save)


@guarded(admin=True,methods=('POST',))
def movements(request):
    data=payload(request)
    def save():
        bank=Bank.objects.get(pk=data['bank'],active=True)
        when=day(data['date'])
        if when<bank.opened_on or when>timezone.localdate():raise ValueError('Date hors de la période du compte.')
        kind=data['kind']
        if kind not in ('expense','income'):raise ValueError('Type de mouvement invalide.')
        amount=money(data['amount'],True)*(-1 if kind=='expense' else 1)
        document=Attachment.objects.get(pk=data['document']) if data.get('document') else None
        item=Movement.objects.create(bank=bank,date=when,label=text(data,'label'),reference=text(data,'reference',150,False),
                                     amount=amount,kind=kind,document=document,actor=request.user)
        return {'id':item.pk}
    return transact(request,data,save)


def post_data(post):
    return {'id':post.pk,'title':post.title,'text':post.text,'category':post.category_id,'category_name':post.category.name,
            'pinned':post.pinned,'date':post.created_at.isoformat(),'author':post.author.get_full_name() or post.author.username,
            'attachments':[{'id':a.pk,'name':a.name,'size':a.size} for a in post.attachments.all()]}


@guarded(methods=('GET','POST'))
def posts(request,pk=None):
    if request.method=='GET':
        items=Post.objects.select_related('author','category').prefetch_related('attachments')
        if request.GET.get('category'):items=items.filter(category_id=int(request.GET['category']))
        if request.GET.get('search'):
            from django.db.models import Q
            search=request.GET['search'][:200];items=items.filter(Q(title__icontains=search)|Q(text__icontains=search))
        page=max(1,int(request.GET.get('page',1)));count=items.count()
        return JsonResponse({'items':[post_data(p) for p in items[(page-1)*30:page*30]],'page':page,'pages':max(1,(count+29)//30),'count':count})
    data=request.POST
    title=text(data,'title');body=text(data,'text',15000);category=Category.objects.get(pk=data['category'],active=True)
    files=request.FILES.getlist('files')
    existing=Post.objects.get(pk=pk) if pk else None
    if len(files)+(existing.attachments.count() if existing else 0)>8:raise ValueError('8 pièces jointes maximum par publication.')
    if sum(file.size for file in files)>12*1024*1024:raise ValueError('12 Mo maximum pour l’ensemble des pièces d’une publication.')
    allowed={'.pdf','.png','.jpg','.jpeg','.txt','.docx','.xlsx','.odt','.ods','.csv'}
    for file in files:
        if Path(file.name).suffix.lower() not in allowed or file.size>10*1024*1024:
            raise ValueError('Pièce jointe refusée : PDF, image, texte ou document bureautique de 10 Mo maximum.')
    stored=[]
    try:
        with transaction.atomic():
            post=Post.objects.select_for_update().get(pk=pk) if pk else Post(author=request.user)
            post.title=title;post.text=body;post.category=category;post.pinned=data.get('pinned')=='true';post.save()
            for file in files:
                item=Attachment(post=post,name=Path(file.name).name[:200],size=file.size)
                item.file.save(file.name,file,save=False);stored.append(item.file);item.save()
            Audit.objects.create(actor=request.user,action='publication',target=str(post.pk))
        return JsonResponse({'id':post.pk})
    except Exception:
        for file in stored:file.delete(save=False)
        raise


@guarded()
def download(request,pk):
    item=Attachment.objects.get(pk=pk)
    try:handle=item.file.open('rb')
    except FileNotFoundError:return JsonResponse({'error':'Pièce absente du stockage. Restaurez la sauvegarde des documents.'},status=404)
    return FileResponse(handle,as_attachment=True,filename=item.name,content_type='application/octet-stream')


@guarded(admin=True,methods=('GET','POST'))
def administration(request,resource):
    if request.method=='GET':
        if resource!='audit':raise ValueError('Rubrique inconnue.')
        return JsonResponse({'items':[{'id':a.pk,'date':a.created_at.isoformat(),'actor':a.actor.username,'action':a.action,'target':a.target} for a in Audit.objects.select_related('actor').order_by('-id')[:100]]})
    data=payload(request)
    def save():
        if resource=='building':
            item=Building.objects.get(pk=1);item.name=text(data,'name');item.address=text(data,'address',500,False);item.save()
        elif resource=='categories':
            item=Category.objects.get(pk=data['id']) if data.get('id') else Category()
            item.name=text(data,'name',80);item.active=boolean(data,'active',True);item.save()
        elif resource=='access':
            item=Owner.objects.select_related('user').get(pk=data['owner'])
            if not item.user:raise ValueError('Créez d’abord le compte de cette personne.')
            if item.user_id==request.user.pk:raise ValueError('Votre propre rôle ne se modifie pas ici.')
            if item.user.is_superuser:raise ValueError('Le compte principal conserve son rôle.')
            item.user.is_staff=boolean(data,'admin');item.user.save(update_fields=['is_staff'])
        else:raise ValueError('Rubrique inconnue.')
        return {'id':item.pk}
    return transact(request,data,save)


@require_http_methods(['GET'])
def health(request):
    Building.objects.count()
    return JsonResponse({'ok':True})


@guarded()
def electorate(request):
    return JsonResponse({'items':[{'owner_id':owner.pk,'name':str(owner),'shares':str(Lot.objects.filter(owner=owner).aggregate(total=Sum('shares'))['total'] or 0),'attendance':'absent','vote':'pending'} for owner in Owner.objects.filter(active=True)],'unassigned_lots':Lot.objects.filter(owner__isnull=True).count()})


@guarded(methods=('POST',), readonly=True)
def tools(request,kind):
    from .calculations import vote_result, split_result, installment_result
    calculations={'vote':vote_result,'split':split_result,'installments':installment_result}
    if kind not in calculations:raise ValueError('Outil inconnu.')
    return JsonResponse(calculations[kind](payload(request)))
