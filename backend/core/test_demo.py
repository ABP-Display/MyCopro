from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.db import transaction
from django.test import TestCase, Client, override_settings
from core.demo import DemoScenario, inspect_demo, AS_OF, KEY, MARKER
from core.models import Owner, Lot
from documents.models import Version, DossierReview
from finance.models import (Organization,FiscalYear,AuditEvent,Entry,Line,FundCall,
    AnnualSettlement,YearClosure,BankStatement,Expense,FundingPolicy,Account)
from finance.services import post_entry,pay_expense
from governance.models import AssemblyWorkflow, AssemblyDecision


class DemoLifecycleTests(TestCase):
    def setUp(self):
        clock=patch('django.utils.timezone.localdate',return_value=AS_OF);clock.start();self.addCleanup(clock.stop)
        directory=TemporaryDirectory();self.addCleanup(directory.cleanup)
        self.directory=Path(directory.name)
        config=override_settings(MEDIA_ROOT=self.directory/'media');config.enable();self.addCleanup(config.disable)
        self.user=get_user_model().objects.create_user('manager',is_staff=True)
        Organization.objects.create(pk=1,name='Organisation à conserver',address='Adresse existante')
        self.original=Owner.objects.create(first_name='Contact',last_name='Existant',email='original@example.test')
        self.lot=Lot.objects.create(number='EXISTANT',owner=self.original,shares=800)
        self.year=FiscalYear.objects.create(name='Exercice existant',starts_on=date(2026,1,1),ends_on=date(2026,12,31))
        self.client.force_login(self.user)

    def seed(self,access=False):
        with transaction.atomic():return DemoScenario(self.user).run(with_access=access)

    def test_full_lifecycle_matches_independent_amounts_and_preserves_existing_data(self):
        report,_,created=self.seed()
        self.assertTrue(created)
        self.assertTrue(all(c['ok'] for c in report['checks']),report['checks'])
        self.assertEqual([r['balance'] for r in report['owners']],['300.00','-250.00','-200.00','1890.00','1360.00'])
        self.assertEqual(report['unpaid_invoices'],'1800.00')
        self.assertEqual(report['calls'],10)
        self.lot.refresh_from_db();self.year.refresh_from_db();self.original.refresh_from_db()
        self.assertEqual((self.lot.number,self.lot.owner_id,self.lot.shares),('EXISTANT',self.original.pk,800))
        self.assertEqual(self.year.name,'Exercice existant')
        self.assertEqual(self.original.first_name,'Contact')
        self.assertFalse(Line.objects.filter(owner=self.original).exists())
        self.assertFalse(Line.objects.filter(lot=self.lot).exists())
        self.assertEqual(Organization.objects.get().name,'Organisation à conserver')
        self.assertEqual(DossierReview.objects.count(),0)
        self.assertEqual(BankStatement.objects.filter(validated=True).count(),3)
        self.assertEqual(AssemblyDecision.objects.count(),4)

    def test_dry_run_is_read_only_and_replay_is_idempotent(self):
        call_command('simulate_copro',stdout=StringIO())
        self.assertEqual(Owner.objects.count(),1)
        self.assertFalse(Entry.objects.exists())
        self.seed()
        before=(Entry.objects.count(),Owner.objects.count(),Version.objects.count(),AssemblyWorkflow.objects.count())
        _,credentials,created=self.seed(access=True)
        self.assertFalse(created);self.assertEqual(credentials,[])
        self.assertEqual(before,(Entry.objects.count(),Owner.objects.count(),Version.objects.count(),AssemblyWorkflow.objects.count()))

    def test_complete_assembly_and_training_assembly_have_real_workflow_states(self):
        self.seed()
        old=AssemblyWorkflow.objects.get(phase='closed')
        self.assertEqual(old.votes.count(),4)
        self.assertTrue(old.minutes['signed_proof'])
        self.assertTrue(old.minutes['required_notifications'])
        self.assertEqual(old.deliveries.filter(kind='minutes').count(),len(old.minutes['required_notifications']))
        training=AssemblyWorkflow.objects.get(phase='convened')
        self.assertEqual(training.votes.count(),0)
        self.assertEqual(training.deliveries.filter(kind='invitation').count(),len(training.packet['electors']))
        response=self.client.get(f'/api/ag/meetings/{training.meeting_id}/workflow/')
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(response.json()['phase'],'convened')

    def test_manager_reports_and_member_confidentiality_and_password_flow(self):
        report,credentials,_=self.seed(access=True)
        self.assertEqual(len(credentials),5)
        self.assertEqual(len(set(c['temporary_password'] for c in credentials)),5)
        for url in [f'/api/finance/cycle/annexes/?year={self.year.pk}',f'/api/finance/cycle/outstanding/?date={AS_OF}',f'/api/finance/banks/?date={AS_OF}',f'/api/finance/reporting/auxiliary/?year={self.year.pk}']:
            response=self.client.get(url)
            self.assertEqual(response.status_code,200,response.content)
        owner=Owner.objects.get(email=credentials[0]['email'])
        member=Client()
        response=member.post('/api/login/',json.dumps({'username':credentials[0]['email'],'password':credentials[0]['temporary_password']}),content_type='application/json')
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(member.get('/api/operations/my-account/').status_code,403)
        changed=member.post('/api/password/',json.dumps({'old_password':credentials[0]['temporary_password'],'new_password':'Test-uniquement!47-Scenarios'}),content_type='application/json')
        self.assertEqual(changed.status_code,200,changed.content)
        response=member.get('/api/operations/my-account/')
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(Decimal(response.json()['balance']),300)
        self.assertNotIn('Bruno',response.content.decode())
        self.assertEqual(Decimal(member.get('/api/operations/my-account/',{'owner':report['owners'][-1]['owner']}).json()['balance']),300)
        self.assertEqual(member.post('/api/finance/receipts/',json.dumps({'owner':owner.pk,'year':self.year.pk,'date':str(AS_OF),'amount':'1'}),content_type='application/json').status_code,403)
        self.assertEqual(member.get('/api/finance/balance/',{'year':self.year.pk}).status_code,403)
        self.assertEqual(member.get(f'/api/ag/meetings/{AssemblyWorkflow.objects.get(phase="closed").meeting_id}/workflow/').status_code,403)

    def test_refuses_existing_accounting_and_rolls_back_on_failure_including_documents(self):
        with transaction.atomic():post_entry(self.year,date(2026,1,1),'AN','Existant',[{'code':'512','debit':'10'},{'code':'450','owner':self.original,'credit':'10'}],self.user,kind='opening')
        with self.assertRaises(ValueError):self.seed()
        self.assertEqual(Owner.objects.count(),1)
        self.assertEqual(Entry.objects.count(),1)

    def test_command_rolls_back_database_and_files_if_output_cannot_be_created(self):
        access=self.directory/'access.md';access.write_text('Ne pas remplacer',encoding='utf-8')
        with self.assertRaises(CommandError):call_command('simulate_copro',apply=True,user='manager',with_access=True,access_file=str(access),stdout=StringIO())
        self.assertEqual(Owner.objects.count(),1)
        self.assertFalse(Entry.objects.exists())
        self.assertEqual(access.read_text(encoding='utf-8'),'Ne pas remplacer')
        self.assertFalse(any(p.is_file() for p in (self.directory/'media').rglob('*')))

    def test_accounting_guards_reject_overpayment_and_future_posting_after_seed(self):
        self.seed()
        expense=Expense.objects.get(reference='DEMO-601-2026')
        from finance.models import BankAccount
        bank=BankAccount.objects.get(account__code='512991')
        with transaction.atomic():
            with self.assertRaises(ValueError):pay_expense(expense,AS_OF,Decimal('900.01'),self.user,bank.pk)
        self.assertEqual(sum(expense.payments.values_list('amount',flat=True)),900)
        with transaction.atomic():
            self.year.refresh_from_db()
            with self.assertRaises(ValueError):post_entry(self.year,date(2026,12,31),'BQ','Futur',[{'code':'512991','debit':'1'},{'code':'450','owner':self.original,'credit':'1'}],self.user)
