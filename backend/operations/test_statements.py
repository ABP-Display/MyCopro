from datetime import date, timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from core.models import Owner
from finance.models import Account, Entry, Line, FiscalYear


class StatementTests(TestCase):
    def setUp(self):
        clock=patch('django.utils.timezone.localdate',return_value=date(2026,10,20));clock.start();self.addCleanup(clock.stop)
        self.manager=get_user_model().objects.create_user('manager',is_staff=True)
        user=get_user_model().objects.create_user('alice')
        self.owner=Owner.objects.create(first_name='Alice',last_name='Test',user=user,email='alice@example.test')
        self.other=Owner.objects.create(first_name='Bruno',last_name='Privé')
        self.client.force_login(user)
        self.year=FiscalYear.objects.create(name='2026',starts_on=date(2026,1,1),ends_on=date(2026,12,31))
        self.account=Account.objects.create(code='450',name='Copropriétaires')
        self.add(self.owner,date(2026,1,1),'100','0','Ancienne charge')
        self.add(self.owner,date(2026,2,1),'0','30','Versement')
        self.add(self.other,date(2026,1,1),'900','0','SECRET BRUNO')

    def add(self,owner,day,debit,credit,label,kind='normal'):
        entry=Entry.objects.create(year=self.year,number=Entry.objects.count()+1,date=day,journal='OD',label=label,created_by=self.manager,kind=kind)
        return Line.objects.create(entry=entry,owner=owner,account=self.account,debit=debit,credit=credit)

    def test_period_balances_omit_carry_and_future_and_ignore_other_owner(self):
        self.add(self.owner,date(2026,2,1),'100','0','Report à ne pas doubler',kind='carry')
        self.add(self.owner,date(2026,12,1),'700','0','Futur')
        result=self.client.get('/api/operations/my-account/',{'from':'2026-02-01','to':'2026-02-28','owner':self.other.pk}).json()
        self.assertEqual(result['balance'],'70.00')
        self.assertEqual(result['opening_balance'],'100.00')
        self.assertEqual(result['closing_balance'],'70.00')
        self.assertEqual(len(result['rows']),1)
        self.assertEqual(result['total_credit'],'30.00')
        self.assertNotIn('SECRET',str(result))

    def test_pagination_and_export_include_movements_older_than_one_hundred(self):
        for i in range(105):self.add(self.owner,date(2026,3,1)+timedelta(days=i),'1','0','Charge '+str(i))
        first=self.client.get('/api/operations/my-account/').json()
        self.assertEqual((first['count'],first['pages'],len(first['rows'])),(107,3,50))
        last=self.client.get('/api/operations/my-account/',{'page':3}).json()
        self.assertEqual(len(last['rows']),7)
        csv=self.client.get('/api/operations/my-account/export/',{'format':'csv','page':3,'owner':self.other.pk})
        text=csv.content.decode('utf-8-sig')
        self.assertIn('Ancienne charge',text);self.assertIn('Charge 104',text)
        self.assertNotIn('SECRET',text)
        self.assertEqual(csv['Cache-Control'],'no-store')
        self.assertIn('Solde final;175.00',text)

    def test_pdf_is_confidential_and_csv_escapes_formula_labels(self):
        self.add(self.owner,date(2026,4,1),'1','0','=HYPERLINK("test")')
        csv=self.client.get('/api/operations/my-account/export/?format=csv').content.decode('utf-8-sig')
        self.assertIn("'=HYPERLINK",csv)
        response=self.client.get('/api/operations/my-account/export/?format=pdf')
        self.assertEqual(response.status_code,200,response.content[:100])
        self.assertTrue(response.content.startswith(b'%PDF'))
        self.assertIn('attachment',response['Content-Disposition'])

    def test_bad_ranges_pages_and_format_are_rejected(self):
        for params in [{'from':'2026-03-01','to':'2026-02-01'},{'from':'bad'},{'to':'2026-12-31'},{'page':0},{'page':999}]:
            self.assertEqual(self.client.get('/api/operations/my-account/',params).status_code,400)
        self.assertEqual(self.client.get('/api/operations/my-account/export/?format=html').status_code,400)
        with patch('operations.statements.MAX_EXPORT',1):
            self.assertEqual(self.client.get('/api/operations/my-account/export/?format=csv').status_code,400)

    def test_anonymous_and_manager_without_owner_have_no_statement(self):
        self.assertEqual(Client().get('/api/operations/my-account/export/').status_code,401)
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get('/api/operations/my-account/export/').status_code,403)
