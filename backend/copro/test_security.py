import json
from datetime import timedelta
from unittest.mock import patch
import pyotp
from django.contrib.auth import get_user_model
from django.test import TestCase,Client
from django.utils import timezone
from .models import MFA,Building
from .security import decrypt


class SecurityTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('alice@example.test',password='InitialPassword1345!')
        Building.objects.create(pk=1)
        self.client.force_login(self.user)
        self.now=timezone.now().replace(microsecond=0)
        clock=patch('django.utils.timezone.now',return_value=self.now);clock.start();self.addCleanup(clock.stop)

    def post(self,path,body,client=None):
        return (client or self.client).post('/api/'+path+'/',json.dumps(body),content_type='application/json')

    def enable(self):
        response=self.post('security/setup',{'current':'InitialPassword1345!'})
        self.assertEqual(response.status_code,200,response.content)
        secret=response.json()['secret']
        response=self.post('security/confirm',{'code':pyotp.TOTP(secret).at(self.now.timestamp())})
        self.assertEqual(response.status_code,200,response.content)
        return secret,response.json()['recovery_codes']

    def challenge(self,client):
        response=self.post('login',{'username':self.user.username,'password':'InitialPassword1345!'},client)
        self.assertEqual(response.status_code,200,response.content)
        self.assertTrue(response.json()['mfa_required'])
        self.assertIsNone(client.get('/api/session/').json()['user'])
        self.assertEqual(client.get('/api/state/').status_code,401)

    def test_enrolment_encrypted_confirmation_timestamp_and_private_status(self):
        response=self.post('security/setup',{'current':'wrong'})
        self.assertEqual(response.status_code,400)
        secret,codes=self.enable()
        item=MFA.objects.get(user=self.user)
        self.assertNotEqual(item.secret,secret);self.assertEqual(decrypt(item.secret),secret)
        self.assertEqual(item.enabled_at,self.now)
        self.assertEqual(len(codes),8)
        self.assertNotIn(codes[0],json.dumps(item.recovery_hashes))
        status=self.client.get('/api/security/').json()
        self.assertTrue(status['mfa_enabled'])
        self.assertNotIn(secret,json.dumps(status))
        self.assertNotIn('recovery_codes',status)
        self.assertEqual(self.post('security/setup',{'current':'InitialPassword1345!'}).status_code,400)
        self.assertEqual(Client().get('/api/security/').status_code,401)

    def test_login_requires_second_factor_and_recovery_is_one_use(self):
        secret,codes=self.enable();client=Client();self.challenge(client)
        response=self.post('login/verify',{'code':pyotp.TOTP(secret).at(self.now.timestamp())},client)
        self.assertEqual(response.status_code,400)  # The activation code was already consumed.
        response=self.post('login/verify',{'code':codes[0]},client)
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(client.get('/api/state/').status_code,200)
        self.assertEqual(len(MFA.objects.get().recovery_hashes),7)
        second=Client();self.challenge(second)
        self.assertEqual(self.post('login/verify',{'code':codes[0]},second).status_code,400)
        with patch('django.utils.timezone.now',return_value=self.now+timedelta(seconds=30)):
            response=self.post('login/verify',{'code':pyotp.TOTP(secret).at((self.now+timedelta(seconds=30)).timestamp())},second)
        self.assertEqual(response.status_code,200,response.content)

    def test_other_sessions_are_invalidated_when_mfa_is_enabled(self):
        old=Client();old.force_login(self.user)
        self.enable()
        self.assertEqual(old.get('/api/state/').status_code,401)
        self.assertIsNone(old.get('/api/session/').json()['user'])
        self.assertEqual(self.client.get('/api/state/').status_code,200)

    def test_pending_setup_and_login_challenges_expire(self):
        response=self.post('security/setup',{'current':'InitialPassword1345!'})
        secret=response.json()['secret']
        with patch('django.utils.timezone.now',return_value=self.now+timedelta(minutes=11)):
            self.assertEqual(self.post('security/confirm',{'code':pyotp.TOTP(secret).now()}).status_code,400)
        self.enable();client=Client();self.challenge(client)
        with patch('django.utils.timezone.now',return_value=self.now+timedelta(minutes=6)):
            self.assertEqual(self.post('login/verify',{'code':'123456'},client).status_code,401)

    def test_disable_requires_password_and_code_and_erases_secrets(self):
        secret,codes=self.enable()
        self.assertEqual(self.post('security/disable',{'current':'wrong','code':codes[0]}).status_code,400)
        self.assertEqual(self.post('security/disable',{'current':'InitialPassword1345!','code':'wrong'}).status_code,400)
        response=self.post('security/disable',{'current':'InitialPassword1345!','code':codes[0]})
        self.assertEqual(response.status_code,200,response.content)
        self.assertFalse(response.json()['mfa_enabled'])
        item=MFA.objects.get();self.assertEqual(item.secret,'');self.assertEqual(item.recovery_hashes,[])
        client=Client();response=self.post('login',{'username':self.user.username,'password':'InitialPassword1345!'},client)
        self.assertIn('user',response.json())

    def test_throttling_is_shared_and_failures_persist(self):
        _,codes=self.enable();first=Client();self.challenge(first)
        for _ in range(5):self.assertEqual(self.post('login/verify',{'code':'wrong'},first).status_code,400)
        second=Client();self.challenge(second)
        self.assertEqual(self.post('login/verify',{'code':codes[0]},second).status_code,429)
        with patch('django.utils.timezone.now',return_value=self.now+timedelta(minutes=5,seconds=1)):
            self.challenge(second)
            self.assertEqual(self.post('login/verify',{'code':codes[0]},second).status_code,200)

    def test_password_change_with_mfa_requires_second_factor(self):
        _,codes=self.enable()
        body={'current':'InitialPassword1345!','password':'DifferentLongPassword789!'}
        self.assertEqual(self.post('password',body).status_code,400)
        response=self.post('password',{**body,'code':codes[0]})
        self.assertEqual(response.status_code,200,response.content)
        self.user.refresh_from_db();self.assertTrue(self.user.check_password(body['password']))
        self.assertEqual(self.client.get('/api/state/').status_code,200)

    def test_password_reset_invalidates_a_pending_login(self):
        _,codes=self.enable();client=Client();self.challenge(client)
        self.user.set_password('AReplacementLongPassword123!');self.user.save()
        self.assertEqual(self.post('login/verify',{'code':codes[0]},client).status_code,401)
