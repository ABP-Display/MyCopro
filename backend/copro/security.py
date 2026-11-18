"""User-owned TOTP enrolment, one-time codes and password-first login challenges."""
import base64
import hashlib
import io
import re
import secrets
import uuid
from datetime import timedelta

import pyotp
import qrcode
import qrcode.image.svg
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.contrib.auth import get_user_model, login, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.views.decorators.http import require_http_methods
from .models import MFA, Audit
from .views import guarded, payload, user_data


def cipher():
    key=hashlib.sha256(('copro.simple.totp.v1:'+settings.SECRET_KEY).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def decrypt(value):
    try:
        return cipher().decrypt(value.encode()).decode()
    except InvalidToken:
        raise ValueError('La clé A2F ne peut pas être lue. Vérifiez la clé de configuration du serveur.')


def status(user):
    item=MFA.objects.filter(user=user).first()
    return {'mfa_enabled':bool(item and item.enabled_at),
            'mfa_enabled_at':item.enabled_at.isoformat() if item and item.enabled_at else None,
            'recovery_remaining':len(item.recovery_hashes) if item else 0}


def recovery_hash(user_id,code):
    normalized=str(code).replace('-','').replace(' ','').upper()
    return salted_hmac('copro.simple.recovery.v1',f'{user_id}:{normalized}').hexdigest()


def blocked(item):
    if item.locked_until and item.locked_until>timezone.now():
        return JsonResponse({'error':'Trop de codes incorrects. Réessayez dans cinq minutes.'},status=429)
    if item.locked_until:
        item.failures=0;item.locked_until=None
    return None


def failure(item,message='Code incorrect, expiré ou déjà utilisé. Attendez le prochain code ou utilisez un code de secours.'):
    item.failures+=1
    if item.failures>=5:item.locked_until=timezone.now()+timedelta(minutes=5)
    item.save()
    return JsonResponse({'error':message},status=400)


def totp_counter(secret,code,last=-1):
    code=str(code).strip().replace(' ','')
    if not re.fullmatch(r'\d{6}',code):return None
    counter=int(timezone.now().timestamp())//30
    totp=pyotp.TOTP(secret)
    for value in (counter,counter-1,counter+1):
        if value>last and secrets.compare_digest(totp.at(value*30),code):return value
    return None


def consume(item,code):
    digest=recovery_hash(item.user_id,code)
    for value in item.recovery_hashes:
        if secrets.compare_digest(value,digest):
            item.recovery_hashes=[v for v in item.recovery_hashes if v!=value]
            return True
    counter=totp_counter(decrypt(item.secret),code,item.last_counter)
    if counter is None:return False
    item.last_counter=counter
    return True


def verified(request,item):
    item.failures=0;item.locked_until=None;item.save()
    request.session['mfa_generation']=str(item.generation)


@guarded(allow_former=True,readonly=True,methods=('GET',))
def information(request):
    return JsonResponse({'user':user_data(request.user),**status(request.user)})


@guarded(allow_former=True,readonly=True,methods=('POST',))
def setup(request):
    data=payload(request)
    with transaction.atomic():
        # Serializes first enrolment as well as subsequent credential changes.
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        item,_=MFA.objects.get_or_create(user=request.user)
        item=MFA.objects.select_for_update().get(pk=item.pk)
        if item.enabled_at:raise ValueError('L’A2F est déjà activée.')
        if result:=blocked(item):return result
        if not request.user.check_password(data.get('current','')):
            return failure(item,'Le mot de passe actuel est incorrect.')
        secret=pyotp.random_base32()
        item.pending_secret=cipher().encrypt(secret.encode()).decode();item.pending_at=timezone.now();item.save()
        uri=pyotp.TOTP(secret).provisioning_uri(name=request.user.email or request.user.username,issuer_name='Copro.')
        qr=qrcode.make(uri,image_factory=qrcode.image.svg.SvgPathImage,box_size=5,border=4)
        output=io.BytesIO();qr.save(output)
        return JsonResponse({'secret':secret,'qr':'data:image/svg+xml;base64,'+base64.b64encode(output.getvalue()).decode(),
                             'created_at':item.pending_at.isoformat(),'expires_at':(item.pending_at+timedelta(minutes=10)).isoformat()})


@guarded(allow_former=True,readonly=True,methods=('POST',))
def confirm(request):
    data=payload(request)
    with transaction.atomic():
        item=MFA.objects.select_for_update().get(user=request.user)
        if item.enabled_at:raise ValueError('L’A2F est déjà activée.')
        if result:=blocked(item):return result
        if not item.pending_at or not item.pending_secret or item.pending_at+timedelta(minutes=10)<timezone.now():
            raise ValueError('La préparation a expiré. Recommencez pour obtenir une nouvelle clé.')
        counter=totp_counter(decrypt(item.pending_secret),data.get('code',''))
        if counter is None:return failure(item)
        codes=['-'.join(secrets.token_hex(2).upper() for _ in range(4)) for _ in range(8)]
        item.secret=item.pending_secret;item.pending_secret='';item.pending_at=None
        item.enabled_at=timezone.now();item.last_counter=counter;item.generation=uuid.uuid4()
        item.recovery_hashes=[recovery_hash(request.user.pk,c) for c in codes]
        verified(request,item)
        Audit.objects.create(actor=request.user,action='security.mfa.enabled')
        return JsonResponse({**status(request.user),'recovery_codes':codes,'user':user_data(request.user)})


@guarded(allow_former=True,readonly=True,methods=('POST',))
def disable(request):
    data=payload(request)
    with transaction.atomic():
        item=MFA.objects.select_for_update().get(user=request.user)
        if not item.enabled_at:raise ValueError('L’A2F n’est pas activée.')
        if result:=blocked(item):return result
        if not request.user.check_password(data.get('current','')):
            return failure(item,'Le mot de passe actuel est incorrect.')
        if not consume(item,data.get('code','')):return failure(item)
        item.secret='';item.pending_secret='';item.pending_at=None;item.enabled_at=None;item.recovery_hashes=[]
        item.last_counter=-1;item.generation=uuid.uuid4();verified(request,item)
        Audit.objects.create(actor=request.user,action='security.mfa.disabled')
        return JsonResponse({'user':user_data(request.user),**status(request.user)})


def begin_login(request,user):
    item=MFA.objects.filter(user=user,enabled_at__isnull=False).first()
    if not item:return None
    request.session.flush()
    request.session['mfa_challenge']={'user':user.pk,'issued':timezone.now().timestamp(),
                                    'password':salted_hmac('copro.mfa.login',user.password).hexdigest(),
                                    'generation':str(item.generation)}
    return JsonResponse({'mfa_required':True,'csrf':get_token(request)})


@require_http_methods(['POST'])
def verify_login(request):
    try:
        data=payload(request)
        pending=request.session.get('mfa_challenge',{})
        if not pending or timezone.now().timestamp()-pending.get('issued',0)>300:
            request.session.pop('mfa_challenge',None)
            return JsonResponse({'error':'La connexion a expiré. Saisissez à nouveau votre mot de passe.'},status=401)
        with transaction.atomic():
            user=get_user_model().objects.select_for_update().get(pk=pending['user'],is_active=True)
            item=MFA.objects.select_for_update().get(user=user,enabled_at__isnull=False)
            if not secrets.compare_digest(salted_hmac('copro.mfa.login',user.password).hexdigest(),pending['password']) or str(item.generation)!=pending['generation']:
                request.session.pop('mfa_challenge',None)
                return JsonResponse({'error':'Votre accès a changé. Recommencez la connexion.'},status=401)
            if result:=blocked(item):return result
            if not consume(item,data.get('code','')):return failure(item)
            login(request,user,backend='django.contrib.auth.backends.ModelBackend')
            request.session.pop('mfa_challenge',None);verified(request,item)
            return JsonResponse({'user':user_data(user),'csrf':get_token(request)})
    except (get_user_model().DoesNotExist,MFA.DoesNotExist,KeyError,ValueError,TypeError):
        return JsonResponse({'error':'Connexion invalide ou expirée. Recommencez.'},status=401)


@guarded(allow_former=True,readonly=True,methods=('POST',))
def change_password(request):
    data=payload(request)
    validate_password(data.get('password',''),request.user)
    with transaction.atomic():
        # All password updates lock the same user as the login verification.
        user=get_user_model().objects.select_for_update().get(pk=request.user.pk)
        item,_=MFA.objects.get_or_create(user=user)
        item=MFA.objects.select_for_update().get(pk=item.pk)
        if result:=blocked(item):return result
        if not user.check_password(data.get('current','')):
            return failure(item,'Le mot de passe actuel est incorrect.')
        if item.enabled_at and not consume(item,data.get('code','')):return failure(item)
        user.set_password(data['password']);user.save(update_fields=['password'])
        update_session_auth_hash(request,user);verified(request,item)
        Audit.objects.create(actor=user,action='security.password.changed')
        return JsonResponse({'ok':True})
