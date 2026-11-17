import json
from datetime import date
from decimal import Decimal
from tempfile import TemporaryDirectory
from uuid import uuid4
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from .models import Building, Owner, Lot, Bank, Movement, Call, Allocation, Payment, Category, Attachment, Post, Ownership
from .calculations import vote_result, split_result, installment_result


class SimpleCoproTests(TestCase):
    def setUp(self):
        temporary=TemporaryDirectory();self.addCleanup(temporary.cleanup)
        media=override_settings(MEDIA_ROOT=temporary.name);media.enable();self.addCleanup(media.disable)
        clock=patch('django.utils.timezone.localdate',return_value=date(2026,11,17));clock.start();self.addCleanup(clock.stop)
        self.admin=get_user_model().objects.create_user('admin',is_staff=True,password='InitialTestPassword123!')
        self.reader=get_user_model().objects.create_user('alice@example.test',password='AliceTestPassword123!')
        self.owner=Owner.objects.create(first_name='Alice',last_name='Exemple',email='alice@example.test',user=self.reader)
        self.other=Owner.objects.create(first_name='Bob',last_name='Exemple',email='bob@example.test')
        self.lot=Lot.objects.create(number='A1',owner=self.owner,shares=120)
        Lot.objects.create(number='B1',owner=self.other,shares=880)
        Building.objects.create(pk=1,name='Test')
        self.bank=Bank.objects.create(name='Courant',holder='Syndicat Test',opened_on=date(2026,1,1),opening_balance=1000)
        self.category=Category.objects.create(name='Travaux')
        self.client.force_login(self.admin)
        self.member=Client();self.member.force_login(self.reader)

    def send(self,path,data=None,client=None):
        return (client or self.client).post('/api/'+path+'/',json.dumps({'request_id':str(uuid4()),**(data or {})}),content_type='application/json')

    def call(self,**changes):
        data={'bank':self.bank.pk,'label':'Charges 2026','kind':'charges','decision':'AG résolution 4','amount':'12000','count':4,'interval':3,'due_date':'2026-01-01',**changes}
        preview=self.send('calls/preview',data)
        self.assertEqual(preview.status_code,200,preview.content)
        response=self.send('calls/create',{**data,'hash':preview.json()['hash']})
        self.assertEqual(response.status_code,200,response.content)
        return Call.objects.get(pk=response.json()['ids'][0])

    def payment(self,call=None,**changes):
        allocation=call.allocations.get(lot=self.lot) if call else None
        return self.send('payments',{'owner':self.owner.pk,'bank':self.bank.pk,'amount':'100','date':'2026-02-01','allocation':allocation.pk if allocation else None,'validate':False,**changes})

    def test_readers_see_shared_pages_but_cannot_mutate_or_read_administration(self):
        state=self.member.get('/api/state/').json()
        self.assertEqual(len(state['owners']),2)
        self.assertEqual(len(state['lots']),2)
        for route in ['owners','lots','banks','calls/preview','calls/create','payments','payments/1/validate','movements','posts','administration/access','administration/categories']:
            response=self.send(route,{},self.member)
            self.assertEqual(response.status_code,403,(route,response.content))
        self.assertEqual(self.member.get('/api/administration/audit/').status_code,403)
        self.assertEqual(Client().get('/api/state/').status_code,401)
        self.assertEqual(self.member.get('/api/ag/electorate/').status_code,200)
        self.assertEqual(self.send('ag/tools/split',{'amount':'10','rows':[{'label':'A','weight':'1'}]},self.member).status_code,200)

    def test_owner_account_creation_login_and_deactivation(self):
        result=self.send('owners',{'first_name':'Claire','last_name':'Test','email':'Claire@example.test','password':'ClaireRandomPassword134!','active':True})
        self.assertEqual(result.status_code,200,result.content)
        owner=Owner.objects.get(pk=result.json()['id'])
        self.assertTrue(owner.user.check_password('ClaireRandomPassword134!'))
        client=Client();r=self.send('login',{'username':'Claire@example.test','password':'ClaireRandomPassword134!'},client)
        self.assertEqual(r.status_code,200,r.content);self.assertFalse(r.json()['user']['admin'])
        self.assertEqual(client.get('/api/state/').status_code,200)
        r=self.send(f'owners/{owner.pk}',{'first_name':'Claire','last_name':'Test','email':owner.email,'active':False})
        self.assertEqual(r.status_code,200,r.content)
        self.assertEqual(client.get('/api/state/').status_code,401)

    def test_calls_conserve_cents_preserve_owner_and_preview_hash(self):
        call=self.call(amount='100.01',count=4)
        self.assertEqual(sum(Call.objects.values_list('amount',flat=True)),Decimal('100.01'))
        self.assertEqual(sum(Allocation.objects.values_list('amount',flat=True)),Decimal('100.01'))
        old_owner=call.allocations.get(lot=self.lot).owner
        r=self.send(f'lots/{self.lot.pk}',{'number':'A1','shares':'120','owner':self.other.pk})
        self.assertEqual(r.status_code,200,r.content)
        self.assertEqual(call.allocations.get(lot=self.lot).owner,old_owner)
        self.assertEqual(Ownership.objects.get().previous,self.owner)
        self.assertEqual(Movement.objects.count(),0)
        data={'bank':self.bank.pk,'label':'Exceptionnel','kind':'exceptional','decision':'AG 5','amount':'100','due_date':'2026-04-01'}
        preview=self.send('calls/preview',data).json()
        self.lot.shares=140;self.lot.save()
        self.assertEqual(self.send('calls/create',{**data,'hash':preview['hash']}).status_code,400)

    def test_validation_changes_bank_once_and_retries_are_idempotent(self):
        call=self.call();response=self.payment(call)
        self.assertEqual(response.status_code,200,response.content)
        pk=response.json()['id'];self.assertEqual(Movement.objects.count(),0)
        token=str(uuid4())
        for _ in range(2):
            r=self.send(f'payments/{pk}/validate',{'request_id':token})
            self.assertEqual(r.status_code,200,r.content)
        self.assertEqual(Movement.objects.count(),1)
        data=self.client.get('/api/state/').json()
        self.assertEqual(data['banks'][0]['balance'],'1100.00')
        self.assertEqual(next(a for a in data['allocations'] if a['lot']==self.lot.pk and a['call']==call.pk)['remaining'],'260.00')
        self.assertEqual(self.send(f'payments/{pk}/validate').status_code,400)

    def test_wrong_payer_and_excess_amount_roll_back(self):
        call=self.call()
        self.assertEqual(self.payment(call,owner=self.other.pk).status_code,400)
        self.assertEqual(self.payment(call,amount='361',validate=True).status_code,400)
        self.assertEqual(Payment.objects.count(),0)
        self.assertEqual(Movement.objects.count(),0)

    def test_pending_can_be_rejected_and_does_not_increase_balance(self):
        r=self.payment();pk=r.json()['id']
        self.assertEqual(self.send(f'payments/{pk}/reject').status_code,200)
        self.assertEqual(self.send(f'payments/{pk}/validate').status_code,400)
        self.assertEqual(Movement.objects.count(),0)

    def test_expense_and_opening_balance_are_preserved(self):
        r=self.send('movements',{'bank':self.bank.pk,'label':'Facture eau','kind':'expense','amount':'250','date':'2026-02-01'})
        self.assertEqual(r.status_code,200,r.content)
        self.assertEqual(self.client.get('/api/state/').json()['banks'][0]['balance'],'750.00')
        r=self.send(f'banks/{self.bank.pk}',{'name':'Courant','holder':'Test','opened_on':'2026-01-01','opening_balance':'2000'})
        self.assertEqual(r.status_code,400)
        self.assertEqual(self.send('movements',{'bank':self.bank.pk,'label':'Future','kind':'expense','amount':'20','date':'2027-01-01'}).status_code,400)

    def test_posts_attachments_filters_and_private_downloads(self):
        file=SimpleUploadedFile('devis.pdf',b'%PDF-1.4 fictional',content_type='application/pdf')
        r=self.client.post('/api/posts/',{'title':'Travaux toiture','text':'Le devis est joint.','category':self.category.pk,'files':file})
        self.assertEqual(r.status_code,200,r.content)
        attachment=Attachment.objects.get()
        self.assertNotIn('devis',attachment.file.name)
        self.assertEqual(self.member.get(f'/api/attachments/{attachment.pk}/').status_code,200)
        self.assertEqual(Client().get(f'/api/attachments/{attachment.pk}/').status_code,401)
        self.assertEqual(self.member.get('/api/posts/?search=toiture').json()['count'],1)
        self.assertEqual(self.member.get('/api/posts/?search=absent').json()['count'],0)
        post=Post.objects.get()
        r=self.client.post(f'/api/posts/{post.pk}/',{'title':'Devis corrigé','text':'Texte relu.','category':self.category.pk})
        self.assertEqual(r.status_code,200,r.content)
        self.assertEqual(Attachment.objects.count(),1)
        self.assertEqual(Post.objects.get().title,'Devis corrigé')
        self.assertEqual(self.member.post(f'/api/posts/{post.pk}/',{'title':'Refus'}).status_code,403)
        evil=SimpleUploadedFile('script.html',b'<script>test</script>')
        self.assertEqual(self.client.post('/api/posts/',{'title':'HTML','text':'Refus','category':self.category.pk,'files':evil}).status_code,400)
        self.assertEqual(Post.objects.count(),1)

    def test_admin_roles_change_server_permissions(self):
        self.assertEqual(self.send('administration/access',{'owner':self.owner.pk,'admin':True}).status_code,200)
        self.assertEqual(self.member.get('/api/administration/audit/').status_code,200)
        self.assertEqual(self.send('administration/access',{'owner':self.owner.pk,'admin':False}).status_code,200)
        self.assertEqual(self.member.get('/api/administration/audit/').status_code,403)

    def test_password_change_and_login_rate_limit(self):
        r=self.send('password',{'current':'AliceTestPassword123!','password':'DifferentLongPassword789!'},self.member)
        self.assertEqual(r.status_code,200,r.content)
        self.reader.refresh_from_db();self.assertTrue(self.reader.check_password('DifferentLongPassword789!'))
        client=Client()
        for _ in range(10):self.assertEqual(self.send('login',{'username':'absent','password':'wrong'},client).status_code,401)
        self.assertEqual(self.send('login',{'username':'absent','password':'wrong'},client).status_code,429)
        self.assertEqual(Client(enforce_csrf_checks=True).post('/api/login/',json.dumps({'username':'x'}),content_type='application/json').status_code,403)

    def test_tools_rounding_and_majority(self):
        result=split_result({'amount':'10','rows':[{'label':'A','weight':1},{'label':'B','weight':1},{'label':'C','weight':1}]})
        self.assertEqual(sum(Decimal(r['amount']) for r in result['rows']),10)
        self.assertEqual(sum(Decimal(r['amount']) for r in installment_result({'amount':'10','count':3})['rows']),10)
        result=vote_result({'rule':'24','total_votes':1000,'total_owners':3,'participating_owners':3,'for_owners':1,'for_votes':400,'against_votes':300,'abstain_votes':300})
        self.assertTrue(result['adopted'])
