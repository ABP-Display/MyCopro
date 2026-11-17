import json
from datetime import date,datetime,timezone as dt_timezone
from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4
from django.test import TestCase,Client,override_settings
from django.contrib.auth import get_user_model
from django.db import transaction
from core.models import Owner,Lot
from documents.models import Version
from governance.models import Meeting,Resolution,AssemblyWorkflow,AssemblyVote,AssemblyDecision
from .models import (FiscalYear,ChargeKey,Account,BankAccount,FundCall,Allocation,Receipt,ReceiptAllocation,CallNotice,Entry,Settlement,Organization)
from .services import post_entry,publish_call
from .cycle import record_mutation

class ResidentJourneyTests(TestCase):
    def setUp(self):
        folder=TemporaryDirectory();self.addCleanup(folder.cleanup)
        settings=override_settings(MEDIA_ROOT=folder.name);settings.enable();self.addCleanup(settings.disable)
        clock=patch('django.utils.timezone.localdate',return_value=date(2026,11,17));clock.start();self.addCleanup(clock.stop)
        self.user=get_user_model().objects.create_user('manager',is_staff=True);self.client.force_login(self.user)
        u=get_user_model().objects.create_user('alice',email='alice@example.test')
        self.alice=Owner.objects.create(first_name='Alice',last_name='Test',email=u.email,user=u)
        self.bob=Owner.objects.create(first_name='Bob',last_name='Test',email='bob@example.test')
        self.member=Client();self.member.force_login(u)
        self.lot=Lot.objects.create(number='A1',owner=self.alice,shares=120)
        Lot.objects.create(number='B1',owner=self.bob,shares=880)
        self.year=FiscalYear.objects.create(name='2026',starts_on=date(2026,1,1),ends_on=date(2026,12,31))
        self.key=ChargeKey.objects.create(name='Charges générales',general=True)
        account=Account.objects.create(code='512001',name='Banque')
        self.bank=BankAccount.objects.create(name='Courant',account=account,is_default=True,iban='FR7630006000011234567890189',bic='AGRIFRPPXXX',holder='Syndicat test')
        Organization.objects.create(pk=1,name='Résidence test')

    def send(self,path,data,client=None):
        return (client or self.client).post('/api/finance/'+path+'/',json.dumps(data),content_type='application/json')

    def prepare(self,**extra):
        body={'year':self.year.pk,'key':self.key.pk,'bank':self.bank.pk,'kind':'current','label':'Charges 2026','amount':'12000','count':4,'interval':3,'first_date':'2026-01-01','decision':'AG du 15/12/2025',**extra}
        preview=self.send('charge-calls/preview',body)
        self.assertEqual(preview.status_code,200,preview.content)
        return body,preview.json()

    def create(self,**extra):
        body,preview=self.prepare(**extra)
        r=self.send('charge-calls/create',{**body,'preview_hash':preview['preview_hash'],'confirmed':True,'request_id':str(uuid4())})
        self.assertEqual(r.status_code,201,r.content);return FundCall.objects.order_by('due_date','id').first()

    def pay(self,call,value='360',**extra):
        allocation=call.allocations.get(lot=self.lot)
        return self.send('resident-payment',{'year':self.year.pk,'owner':self.alice.pk,'amount':value,'date':'2026-02-01','bank':self.bank.pk,'confirmed':True,'links':[{'allocation':allocation.pk,'amount':value}],**extra})

    def test_preview_conserves_cents_and_creates_nothing(self):
        body,data=self.prepare(amount='100.01',count=3,interval=3)
        self.assertEqual(sum(Decimal(p['amount']) for p in data['parts']),Decimal('100.01'))
        for part in data['parts']:self.assertEqual(sum(Decimal(r['amount']) for r in part['rows']),Decimal(part['amount']))
        self.assertEqual(FundCall.objects.count(),0)
        self.lot.shares=121;self.lot.save()
        r=self.send('charge-calls/create',{**body,'confirmed':True,'preview_hash':data['preview_hash']})
        self.assertEqual(r.status_code,400);self.assertEqual(FundCall.objects.count(),0)

    def test_calls_quarters_future_and_idempotency(self):
        body,preview=self.prepare();body.update(confirmed=True,preview_hash=preview['preview_hash'],request_id=str(uuid4()))
        self.assertEqual(self.send('charge-calls/create',body).status_code,201)
        self.assertEqual(self.send('charge-calls/create',body).status_code,201)
        self.assertEqual(FundCall.objects.count(),4)
        self.assertEqual(Allocation.objects.filter(lot=self.lot).aggregate(v=__import__('django').db.models.Sum('amount'))['v'],1440)
        nextyear=FiscalYear.objects.create(name='2027',starts_on=date(2027,1,1),ends_on=date(2027,12,31))
        self.create(year=nextyear.pk,first_date='2027-01-01')
        self.assertEqual(FundCall.objects.filter(year=nextyear,entry__isnull=False).count(),0)

    def test_adopted_budget_limit_and_reference(self):
        meeting=Meeting.objects.create(title='AG',scheduled_at=datetime(2025,12,1,tzinfo=dt_timezone.utc),created_by=self.user)
        resolution=Resolution.objects.create(meeting=meeting,position=1,title='Budget',text='Adopté',majority='24')
        workflow=AssemblyWorkflow.objects.create(meeting=meeting,phase='signed')
        vote=AssemblyVote.objects.create(workflow=workflow,resolution=resolution,data={},recorded_by=self.user)
        source=AssemblyDecision.objects.create(vote=vote,kind='budget',data={'year':self.year.pk,'lines':[{'key':self.key.pk,'amount':'12000'}],'reference':'AG 1 résolution 1'},created_by=self.user)
        self.create(amount='6000')  # Existing calls also consume the voted annual ceiling.
        self.create(source_decision=source.pk,amount='6000')
        call=FundCall.objects.filter(source_decision=source).first()
        self.assertEqual(call.source_decision_id,source.pk);self.assertEqual(call.decision,'AG 1 résolution 1')
        bad={'year':self.year.pk,'key':self.key.pk,'bank':self.bank.pk,'amount':'1','count':1,'first_date':'2026-11-01','source_decision':source.pk}
        self.assertEqual(self.send('charge-calls/preview',bad).status_code,400)

    def test_receipt_matches_lot_and_calendar_cash_totals(self):
        call=self.create();r=self.pay(call,'100');self.assertEqual(r.status_code,201,r.content)
        self.assertEqual(ReceiptAllocation.objects.get().allocation.lot_id,self.lot.pk)
        self.assertEqual(Settlement.objects.filter(active=True).count(),1)
        data=self.member.get('/api/finance/my-resident/?year=2026').json()
        self.assertEqual(Decimal(data['summary']['paid']),100)
        self.assertEqual(data['receipts'][0]['lots'][0]['number'],'A1')
        self.assertNotIn('Bob',json.dumps(data))
        statement=self.client.get(f'/api/finance/banks/{self.bank.pk}/movements/?from=2026-02-01&to=2026-02-28')
        self.assertEqual(statement.status_code,200,statement.content)
        self.assertEqual(statement.json()['items'][0]['paid_for'],[{'lot':'A1','call':call.label,'amount':'100.00'}])
        receipt=Receipt.objects.get()
        with transaction.atomic():
            self.year.refresh_from_db()
            post_entry(self.year,date(2026,3,1),'OD','Correction sans encaissement',[{'code':'450','owner':self.alice,'credit':20},{'code':'701','debit':20}],self.user)
        data=self.member.get('/api/finance/my-resident/?year=2026').json()
        self.assertEqual(Decimal(data['summary']['paid']),100)

    def test_overpayment_and_wrong_owner_roll_back_all(self):
        call=self.create();before=Entry.objects.count()
        self.assertEqual(self.pay(call,'361').status_code,400)
        self.assertEqual(self.pay(call,'100',owner=self.bob.pk).status_code,400)
        self.assertEqual(Entry.objects.count(),before);self.assertFalse(Receipt.objects.exists())

    def test_old_receipt_can_be_explicitly_linked_without_new_money(self):
        call=self.create()
        r=self.pay(call,'100',links=[]);self.assertEqual(r.status_code,201,r.content)
        count=Entry.objects.count();receipt=Receipt.objects.get()
        r=self.send('resident-payment',{'receipt':receipt.pk,'confirmed':True,'links':[{'allocation':call.allocations.get(lot=self.lot).pk,'amount':'100'}]})
        self.assertEqual(r.status_code,201,r.content);self.assertEqual(Entry.objects.count(),count)
        self.assertEqual(Decimal(r.json()['lot_unassigned']),0)

    def test_already_matched_historical_receipt_can_be_labelled_by_lot(self):
        from .cycle import match_lines
        call=self.create();self.pay(call,'100',links=[])
        receipt=Receipt.objects.get();allocation=call.allocations.get(lot=self.lot)
        with transaction.atomic():
            match_lines(call.entry.lines.get(owner=self.alice),receipt.entry.lines.get(owner=self.alice),Decimal('100'),self.user)
        entries=Entry.objects.count();matches=Settlement.objects.count()
        r=self.send('resident-payment',{'receipt':receipt.pk,'confirmed':True,'links':[{'allocation':allocation.pk,'amount':'60'}]})
        self.assertEqual(r.status_code,201,r.content)
        self.assertEqual(Entry.objects.count(),entries);self.assertEqual(Settlement.objects.count(),matches)
        r=self.send('resident-payment',{'receipt':receipt.pk,'confirmed':True,'links':[{'allocation':allocation.pk,'amount':'40'}]})
        self.assertEqual(r.status_code,201,r.content)
        self.assertEqual(sum(ReceiptAllocation.objects.values_list('amount',flat=True)),100)
        self.assertEqual(Decimal(r.json()['lot_unassigned']),0)

    def test_seller_money_and_historical_debt_stay_after_sale(self):
        call=self.create();self.pay(call,'100')
        old_owner=call.allocations.get(lot=self.lot).owner_id
        with transaction.atomic():record_mutation({'lot':self.lot.pk,'new_owner':self.bob.pk,'effective_date':'2026-06-01','reference':'Vente notifiée'},self.user)
        self.assertEqual(Receipt.objects.get().owner_id,self.alice.pk)
        self.assertEqual(call.allocations.get(lot=self.lot).owner_id,old_owner)
        data=self.client.get(f'/api/finance/lot-history/{self.lot.pk}/').json()
        self.assertEqual(data['payments'][0]['owner'],str(self.alice))
        self.assertEqual(data['ownerships'][0]['to'],str(self.bob))
        self.assertEqual(Decimal(self.member.get('/api/finance/my-resident/?year=2026').json()['summary']['paid']),100)
        r=self.client.patch(f'/api/lots/{self.lot.pk}/',json.dumps({'owner':self.alice.pk}),content_type='application/json')
        self.assertEqual(r.status_code,400)

    def test_notices_are_private_immutable_and_idempotent(self):
        call=self.create();r=self.send(f'call-notices/{call.pk}',{'confirmed':True})
        self.assertEqual(r.status_code,201,r.content);self.assertEqual(CallNotice.objects.count(),2)
        self.send(f'call-notices/{call.pk}',{'confirmed':True});self.assertEqual(CallNotice.objects.count(),2)
        notice=CallNotice.objects.get(owner=self.alice)
        shared=self.client.patch(f'/api/documents/items/{notice.version.document_id}/',json.dumps({'published':True}),content_type='application/json')
        self.assertEqual(shared.status_code,400)
        original=notice.version.checksum;self.bank.iban='FR1420041010050500013M02606';self.bank.save()
        notice.refresh_from_db();self.assertEqual(notice.version.checksum,original)
        self.assertEqual(notice.snapshot['bank']['iban'],'FR7630006000011234567890189')
        response=self.member.get(f'/api/finance/notice-download/{notice.pk}/');self.assertEqual(response.status_code,200);self.assertTrue(b''.join(response.streaming_content).startswith(b'%PDF-'))
        other=CallNotice.objects.get(owner=self.bob)
        self.assertEqual(self.member.get(f'/api/finance/notice-download/{other.pk}/?owner={self.alice.pk}').status_code,404)
        self.assertEqual(Client().get(f'/api/finance/notice-download/{notice.pk}/').status_code,401)
        self.assertEqual(self.member.get(f'/api/finance/lot-history/{self.lot.pk}/').status_code,403)

    def test_old_year_payments_remain_separate(self):
        old=FiscalYear.objects.create(name='2025',starts_on=date(2025,1,1),ends_on=date(2025,12,31))
        r=self.send('resident-payment',{'year':old.pk,'owner':self.alice.pk,'amount':'200','date':'2025-12-31','bank':self.bank.pk,'confirmed':True})
        self.assertEqual(r.status_code,201,r.content)
        self.assertEqual(Decimal(self.member.get('/api/finance/my-resident/?year=2025').json()['summary']['paid']),200)
        self.assertEqual(Decimal(self.member.get('/api/finance/my-resident/?year=2026').json()['summary']['paid']),0)
