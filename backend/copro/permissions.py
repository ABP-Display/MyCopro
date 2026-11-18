from django.db.models import Q
from .models import Owner, Lot, Ownership, Post


def manager(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def profile(user):
    return Owner.objects.filter(user=user).first() if user.is_authenticated else None


def former(owner):
    return bool(owner and not Lot.objects.filter(owner=owner).exists() and Ownership.objects.filter(previous=owner).exists())


def archived_user(user):
    return not manager(user) and former(profile(user))


def visible_posts(user):
    items=Post.objects.all()
    if not user.is_authenticated:return items.none()
    if manager(user):return items
    owner=profile(user)
    personal=Q(scope='owner',recipient=owner) if owner else Q(pk__in=[])
    if former(owner):return items.filter(personal)
    return items.filter(Q(scope='copro')|personal|(Q(scope='lot',lot__owner=owner) if owner else Q(pk__in=[])))


def owner_at(lot,when):
    owner=lot.owner
    for change in Ownership.objects.filter(lot=lot,date__gt=when).select_related('previous').order_by('-date','-id'):
        owner=change.previous
    return owner
