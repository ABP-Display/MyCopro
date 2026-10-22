import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from core.models import Owner
from finance.models import Organization, FiscalYear, Account, Entry, Line, AuditEvent
from operations.models import Supplier
from .models import Document, Version


class TemplateTests(TestCase):
    def setUp(self):
        directory=TemporaryDirectory();self.addCleanup(directory.cleanup)
        self.directory=Path(directory.name)
        setting=override_settings(MEDIA_ROOT=self.directory);setting.enable();self.addCleanup(setting.disable)
        self.manager=get_user_model().objects.create_user('manager',is_staff=True)
        self.client.force_login(self.manager)
        user=get_user_model().objects.create_user('alice')
        self.owner=Owner.objects.create(first_name='Alice',last_name='Test',email='alice@example.test',user=user)
        self.member=Client();self.member.force_login(user)
        Organization.objects.create(pk=1,name='Résidence de test',address='12 rue Exemple',email='syndic@example.test')
        self.supplier=Supplier.objects.create(name='Entreprise de test',email='devis@example.test',address='24 rue Exemple',created_by=self.manager)

    def fields(self,key='information',**query):
        response=self.client.get(f'/api/documents/templates/{key}/',query)
        self.assertEqual(response.status_code,200,response.content)
        data=response.json()['fields'];data['body']='Texte relu et complété.\nPas de HTML : <script>test</script>'
        return data

    def save(self,key,fields,**kw):
        return self.client.post(f'/api/documents/templates/{key}/',json.dumps({'fields':fields,'reviewed':True,**kw}),content_type='application/json')

    def test_catalog_defaults_and_private_versioned_output(self):
        catalog=self.client.get('/api/documents/templates/').json()
        self.assertEqual(len(catalog['items']),4)
        self.assertEqual(catalog['owners'][0]['name'],'Alice Test')
        fields=self.fields(owner=self.owner.pk)
        self.assertEqual(fields['recipient'],'Alice Test')
        self.assertIn('Résidence de test',fields['subject'])
        response=self.save('information',fields)
        self.assertEqual(response.status_code,201,response.content)
        doc=Document.objects.get(pk=response.json()['id'])
        self.assertFalse(doc.published);self.assertEqual(doc.folder.name,'Courriers préparés')
        self.assertEqual(doc.versions.count(),1)
        pdf=self.client.get(response.json()['download'])
        self.assertTrue(b''.join(pdf.streaming_content).startswith(b'%PDF'))
        self.assertEqual(self.member.get(response.json()['download']).status_code,404)
        self.assertTrue(AuditEvent.objects.filter(action='document.template.create').exists())

    def test_supplier_prefill_and_all_letter_types(self):
        for key in ['quote','intervention']:
            fields=self.fields(key,supplier=self.supplier.pk)
            self.assertEqual(fields['recipient'],'Entreprise de test')
            self.assertIn('devis@example.test',fields['recipient_address'])
            self.assertEqual(self.save(key,fields).status_code,201)

    def test_member_and_anonymous_cannot_read_or_create_templates(self):
        self.assertEqual(Client().get('/api/documents/templates/').status_code,401)
        self.assertEqual(self.member.get('/api/documents/templates/').status_code,403)
        self.assertEqual(self.member.get('/api/documents/templates/information/').status_code,403)
        self.assertEqual(self.member.post('/api/documents/templates/information/',json.dumps({}),content_type='application/json').status_code,403)
        self.assertEqual(Document.objects.count(),0)

    def test_incomplete_unreviewed_and_invalid_fields_create_nothing(self):
        incomplete=self.client.get('/api/documents/templates/information/').json()['fields']
        self.assertEqual(self.save('information',incomplete).status_code,400)
        fields=self.fields()
        self.assertEqual(self.save('information',fields,reviewed=False).status_code,400)
        self.assertEqual(self.save('information',{**fields,'body':'x'*20001}).status_code,400)
        self.assertEqual(self.save('information',{**fields,'date':'incorrect'}).status_code,400)
        self.assertEqual(self.save('information',{**fields,'published':True}).status_code,400)
        self.assertEqual(Document.objects.count(),0)

    def test_reminder_uses_current_balance_without_assuming_overdue(self):
        self.assertEqual(self.client.get('/api/documents/templates/reminder/').status_code,400)
        self.assertEqual(self.client.get('/api/documents/templates/reminder/',{'owner':self.owner.pk}).status_code,400)
        year=FiscalYear.objects.create(name='Année',starts_on=date(2026,1,1),ends_on=date(2026,12,31))
        account=Account.objects.create(code='450',name='Copropriétaires')
        entry=Entry.objects.create(year=year,number=1,date=date(2026,1,1),journal='OD',label='Charge',created_by=self.manager)
        Line.objects.create(entry=entry,owner=self.owner,account=account,debit=120)
        result=self.client.get('/api/documents/templates/reminder/',{'owner':self.owner.pk}).json()['fields']
        self.assertIn('120,00',result['body']);self.assertIn('ne suffit pas',result['body'])
        self.assertEqual(self.save('reminder',result).status_code,201)

    def test_storage_is_cleaned_if_post_upload_audit_fails(self):
        fields=self.fields()
        original=AuditEvent.objects.create
        def fail(**kw):
            if kw.get('action')=='document.template.create':raise ValueError('Échec simulé')
            return original(**kw)
        with patch.object(AuditEvent.objects,'create',side_effect=fail):
            self.assertEqual(self.save('information',fields).status_code,400)
        self.assertEqual(Document.objects.count(),0);self.assertEqual(Version.objects.count(),0)
        self.assertFalse(any(p.is_file() for p in self.directory.rglob('*')))
