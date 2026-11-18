import hashlib
import json
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from .models import Lot, Owner, Ownership, Post, Reply, Category, Allocation, Audit
from .permissions import manager, archived_user, visible_posts
from .views import guarded, payload, text, day, transact, allocation_data
from .uploads import validate_files, write_files


def accessible_lot(user, pk):
    lot=Lot.objects.get(pk=pk)
    if not manager(user) and (archived_user(user) or not Owner.objects.filter(pk=lot.owner_id,user=user).exists()):raise Lot.DoesNotExist
    return lot


def accessible_owner(user, pk):
    owner=Owner.objects.get(pk=pk)
    if not manager(user) and owner.user_id!=user.pk:raise Owner.DoesNotExist
    return owner


@guarded(allow_former=True)
def dossier(request, kind, pk):
    if kind=='lots':
        item=accessible_lot(request.user,pk)
        owner=item.owner
        allocations=Allocation.objects.filter(lot=item)
        if not manager(request.user):allocations=allocations.filter(owner=owner)
        history=[{'date':str(h.date),'previous':h.previous_name or str(h.previous or 'Non affecté'),'owner':h.owner_name or str(h.owner or 'Non affecté'),'reference':h.reference} for h in Ownership.objects.filter(lot=item).order_by('-date','-id')]
        title=f'Lot {item.number}'
    elif kind=='owners':
        item=owner=accessible_owner(request.user,pk);title=str(owner)
        allocations=Allocation.objects.filter(owner=owner);history=[]
    else:raise ValueError('Dossier inconnu.')
    return JsonResponse({'title':title,'owner':owner.pk if owner else None,'history':history,
        'allocations':[allocation_data(a) for a in allocations.select_related('call','lot','owner')],
        'payments':list(owner.payment_set.values('id','lot_id','date','amount','status','reference')) if owner else [],
        'categories':list(Category.objects.values('id','name','active')),'archived':archived_user(request.user)})


def transfer_plan(data):
    ids=data.get('lots',[])
    if not isinstance(ids,list) or not ids or len(ids)>100 or len(set(ids))!=len(ids):raise ValueError('Choisissez de 1 à 100 lots différents.')
    lots=list(Lot.objects.filter(pk__in=ids).select_related('owner').order_by('pk'))
    if len(lots)!=len(ids):raise ValueError('Lot introuvable.')
    owner=Owner.objects.get(pk=data['owner'],active=True)
    if not owner.user_id:raise ValueError('Créez d’abord le compte du nouveau propriétaire.')
    when=day(data['date']);reference=text(data,'reference',250)
    if when>timezone.localdate():raise ValueError('La passation doit être effective aujourd’hui ou dans le passé.')
    for lot in lots:
        if lot.owner_id==owner.pk:raise ValueError('Un lot appartient déjà à ce propriétaire.')
        last=Ownership.objects.filter(lot=lot).order_by('-date','-id').first()
        if last and when<last.date:raise ValueError('La date précède une passation déjà enregistrée.')
    rows=[{'id':l.pk,'number':l.number,'previous':l.owner_id,'previous_name':str(l.owner or 'Non affecté'),'shares':str(l.shares)} for l in lots]
    result={'lots':rows,'owner':owner.pk,'name':str(owner),'date':str(when),'reference':reference,
        'notice':'Les appels, paiements et documents personnels existants restent à leur destinataire. Les demandes ouvertes sur ces lots sont clôturées. Vérifiez séparément les droits administrateur du partant.'}
    result['hash']=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
    return result,lots,owner,when


@guarded(admin=True,methods=('POST',))
def transfer(request, action):
    data=payload(request)
    if action=='preview':return JsonResponse(transfer_plan(data)[0])
    if action!='confirm':raise ValueError('Action inconnue.')
    def save():
        plan,lots,owner,when=transfer_plan(data)
        if data.get('hash')!=plan['hash']:raise ValueError('L’aperçu a changé. Recommencez la vérification.')
        for lot in lots:
            Ownership.objects.create(lot=lot,previous=lot.owner,owner=owner,date=when,actor=request.user,reference=plan['reference'],previous_name=str(lot.owner or ''),owner_name=str(owner))
            Post.objects.filter(lot=lot,recipient=lot.owner,kind='request').exclude(status='closed').update(status='closed')
            lot.owner=owner;lot.save(update_fields=['owner'])
        return {'id':owner.pk,'lots':[l.pk for l in lots]}
    return transact(request,data,save)


@guarded(methods=('POST',),readonly=True,allow_former=True)
def respond(request, pk):
    files=request.FILES.getlist('files');validate_files(files);stored=[]
    try:
        with transaction.atomic():
            post=visible_posts(request.user).select_for_update(of=('self',)).get(pk=pk,kind='request')
            if archived_user(request.user) or post.status=='closed':raise ValueError('Cette demande est clôturée ou archivée.')
            if not manager(request.user) and post.recipient.user_id!=request.user.pk:raise Post.DoesNotExist
            if post.lot_id and post.lot.owner_id!=post.recipient_id:raise ValueError('Le propriétaire du lot a changé. Créez une nouvelle demande.')
            reply=Reply.objects.create(post=post,owner=post.recipient,author=request.user,text=text(request.POST,'text',15000))
            write_files(post,files,stored,reply);post.status='answered';post.save(update_fields=['status'])
            Audit.objects.create(actor=request.user,action='réponse à une demande',target=str(post.pk))
        return JsonResponse({'id':reply.pk})
    except Exception:
        for file in stored:file.delete(save=False)
        raise


@guarded(admin=True,methods=('POST',))
def close(request,pk):
    def save():
        post=Post.objects.get(pk=pk,kind='request');post.status='closed';post.save(update_fields=['status']);return {'id':post.pk}
    return transact(request,payload(request),save)
