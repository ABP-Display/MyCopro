import uuid
from django.conf import settings
from django.db import models


class Building(models.Model):
    name = models.CharField(max_length=150, default='Ma copropriété')
    address = models.CharField(max_length=500, blank=True)


class Owner(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    active = models.BooleanField(default=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)

    class Meta:
        ordering = ['last_name','first_name','id']

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class Lot(models.Model):
    number = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=200, blank=True)
    shares = models.DecimalField(max_digits=12, decimal_places=2)
    owner = models.ForeignKey(Owner, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        ordering = ['number','id']
        constraints = [models.CheckConstraint(condition=models.Q(shares__gt=0), name='simple_lot_positive_shares')]


class Ownership(models.Model):
    lot = models.ForeignKey(Lot, on_delete=models.PROTECT)
    previous = models.ForeignKey(Owner, on_delete=models.PROTECT, related_name='+', null=True)
    owner = models.ForeignKey(Owner, on_delete=models.PROTECT, related_name='+', null=True)
    date = models.DateField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reference = models.CharField(max_length=250, blank=True)
    previous_name = models.CharField(max_length=201, blank=True)
    owner_name = models.CharField(max_length=201, blank=True)


class Bank(models.Model):
    name = models.CharField(max_length=150)
    institution = models.CharField(max_length=150, blank=True)
    holder = models.CharField(max_length=150)
    iban = models.CharField(max_length=34, blank=True)
    bic = models.CharField(max_length=11, blank=True)
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    opened_on = models.DateField()
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']


class Call(models.Model):
    label = models.CharField(max_length=150)
    kind = models.CharField(max_length=15, choices=[('charges','Charges courantes'),('works','Fonds travaux'),('exceptional','Appel exceptionnel')])
    decision = models.CharField(max_length=250)
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    bank = models.ForeignKey(Bank, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-due_date','-id']


class Allocation(models.Model):
    call = models.ForeignKey(Call, on_delete=models.PROTECT, related_name='allocations')
    lot = models.ForeignKey(Lot, on_delete=models.PROTECT)
    owner = models.ForeignKey(Owner, on_delete=models.PROTECT)
    shares = models.DecimalField(max_digits=12, decimal_places=2)
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['call','lot'], name='simple_call_lot_unique')]


class Payment(models.Model):
    owner = models.ForeignKey(Owner, on_delete=models.PROTECT)
    lot = models.ForeignKey(Lot, on_delete=models.PROTECT, null=True, blank=True)
    allocation = models.ForeignKey(Allocation, on_delete=models.PROTECT, null=True, blank=True)
    bank = models.ForeignKey(Bank, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    date = models.DateField()
    reference = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=12, default='pending', choices=[('pending','À vérifier'),('validated','Validé'),('rejected','Écarté')])
    validated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name='+')
    validated_at = models.DateTimeField(null=True)

    class Meta:
        ordering = ['-date','-id']
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name='simple_payment_positive')]


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']


class Post(models.Model):
    scope = models.CharField(max_length=10, default='copro', choices=[('copro','Copropriété'),('lot','Technique du lot'),('owner','Personnel')])
    lot = models.ForeignKey(Lot, on_delete=models.PROTECT, null=True, blank=True)
    recipient = models.ForeignKey(Owner, on_delete=models.PROTECT, null=True, blank=True, related_name='personal_posts')
    recipient_name = models.CharField(max_length=201, blank=True)
    lot_number = models.CharField(max_length=30, blank=True)
    kind = models.CharField(max_length=10, default='info', choices=[('info','Information / document'),('call','Appel de charges'),('request','Demande de renseignement')])
    status = models.CharField(max_length=10, default='open', choices=[('open','En cours'),('answered','Réponse reçue'),('closed','Clôturé')])
    due_on = models.DateField(null=True, blank=True)
    title = models.CharField(max_length=150)
    text = models.TextField(max_length=15000)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    pinned = models.BooleanField(default=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-pinned','-created_at','-id']


def attachment_path(instance, filename):
    return f'attachments/{uuid.uuid4().hex}'


class Reply(models.Model):
    post = models.ForeignKey(Post, on_delete=models.PROTECT, related_name='replies')
    owner = models.ForeignKey(Owner, on_delete=models.PROTECT)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    text = models.TextField(max_length=15000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at','id']


class Attachment(models.Model):
    reply = models.ForeignKey(Reply, on_delete=models.PROTECT, null=True, blank=True, related_name='attachments')
    post = models.ForeignKey(Post, on_delete=models.PROTECT, related_name='attachments')
    file = models.FileField(upload_to=attachment_path)
    name = models.CharField(max_length=200)
    size = models.PositiveIntegerField()


class Movement(models.Model):
    bank = models.ForeignKey(Bank, on_delete=models.PROTECT, related_name='movements')
    date = models.DateField()
    label = models.CharField(max_length=150)
    reference = models.CharField(max_length=150, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment = models.OneToOneField(Payment, on_delete=models.PROTECT, null=True, blank=True)
    document = models.ForeignKey(Attachment, on_delete=models.PROTECT, null=True, blank=True)
    kind = models.CharField(max_length=15, choices=[('payment','Paiement copropriétaire'),('expense','Dépense'),('income','Autre recette')])
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ['-date','-id']
        constraints = [models.CheckConstraint(condition=~models.Q(amount=0), name='simple_movement_nonzero')]


class Operation(models.Model):
    token = models.UUIDField(unique=True)
    fingerprint = models.CharField(max_length=64)
    response = models.JSONField()


class Audit(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=100)
    target = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class LoginAttempt(models.Model):
    key = models.CharField(max_length=64, unique=True)
    count = models.PositiveIntegerField(default=0)
    since = models.DateTimeField()


class MFA(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    secret = models.TextField(blank=True)
    pending_secret = models.TextField(blank=True)
    pending_at = models.DateTimeField(null=True)
    enabled_at = models.DateTimeField(null=True)
    last_counter = models.BigIntegerField(default=-1)
    recovery_hashes = models.JSONField(default=list)
    generation = models.UUIDField(default=uuid.uuid4)
    failures = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True)
