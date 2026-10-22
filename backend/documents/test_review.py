from datetime import date, datetime, timezone as dt_timezone
from io import BytesIO
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from django.test import TestCase, Client, override_settings
from core.models import Owner, Lot
from council.models import Mandate
from finance.models import Organization, FiscalYear, ChargeKey, FinanceProject, FundCall, Line, Budget, Account, YearClosure
from finance.services import post_entry, publish_call, record_expense
from finance.cycle import annexes, finish_project, close_year, regularization_data
from governance.models import Meeting, Resolution, AssemblyWorkflow
from documents.models import Document, Version, DossierReview
from documents import review
from documents.pdf import render


class DocumentReviewTests(TestCase):
    def setUp(self):
        clock=patch('django.utils.timezone.localdate',return_value=date(2026,10,15));clock.start();self.addCleanup(clock.stop)
        directory=TemporaryDirectory();self.addCleanup(directory.cleanup)
        settings=override_settings(MEDIA_ROOT=directory.name);settings.enable();self.addCleanup(settings.disable)
        self.user=get_user_model().objects.create_user('manager',is_staff=True)
        self.client.force_login(self.user)
        Organization.objects.create(pk=1,name='Résidence fictive des Tilleuls',address='12 rue des Tilleuls, 59000 Lille',email='syndic@example.test')
        self.year=FiscalYear.objects.create(name='2025',starts_on=date(2025,1,1),ends_on=date(2025,12,31))
        self.next=FiscalYear.objects.create(name='2026',starts_on=date(2026,1,1),ends_on=date(2026,12,31))
        self.key=ChargeKey.objects.create(name='Charges générales')
        self.owner=Owner.objects.create(first_name='Alice',last_name='Martin')
        self.other=Owner.objects.create(first_name='Benoît',last_name='Petit')
        self.lot=Lot.objects.create(number='A',owner=self.owner,shares=600)
        Lot.objects.create(number='B',owner=self.other,shares=400)
        doc=Document.objects.create(title='Rapport fictif de relecture')
        content=b'%PDF-1.4\nFictitious signed review for tests only\n%%EOF'
        self.proof=Version(document=doc,filename='rapport-test.pdf',size=len(content),content_type='application/pdf',checksum=hashlib.sha256(content).hexdigest(),created_by=self.user)
        self.proof.file.save('rapport.pdf',ContentFile(content));doc.current=self.proof;doc.save()
        self.url=f'/api/documents/validation/accounting/{self.year.pk}/'

    def post(self,data,status=201,url=None,client=None):
        response=(client or self.client).post(url or self.url,json.dumps(data),content_type='application/json')
        self.assertEqual(response.status_code,status,response.content)
        return response

    def data(self,kind='accounting',pk=None):
        return dict(kind='forged-unused-kind',source_hash=review.source(kind,pk or self.year.pk)['source_hash'],
            verdict='approved',reviewer='Relecteur fictif',qualification='Contrôleur — exemple',reviewed_on='2026-10-15',
            observations='Dossier de test uniquement, aucun avis professionnel réel.',proof=self.proof.pk,
            checks={key:True for key in review.CHECKLISTS[kind]},declaration_confirmed=True)

    def representative(self):
        project=FinanceProject.objects.create(name='Toiture',key=self.key,budget=500,decision='AG du 15 mars 2025',decided_on=date(2025,3,15))
        with transaction.atomic():
            for kind,value,p in [('current',1000,None),('works',500,project)]:
                call=FundCall.objects.create(year=self.year,key=self.key,label='Appel '+kind,date=date(2025,4,1),due_date=date(2025,4,1),amount=value,kind=kind,project=p,decision='AG')
                publish_call(call,self.user)
            for value,p in [(600,None),(300,project)]:
                record_expense(dict(year=self.year.pk,key=self.key.pk,supplier='Entreprise fictive',reference='F-'+str(value),label='Entretien',date='2025-06-01',amount=str(value),**({'project':p.pk} if p else {})),self.user)
        return project

    def test_representative_dossier_matches_independent_oracle(self):
        self.representative()
        oracle=json.loads((Path(__file__).parent/'fixtures'/'annual-review-oracle.json').read_text(encoding='utf-8'))
        pack=annexes(self.year)['regulatory']
        self.assertEqual(pack['errors'],[])
        state=pack['annexes'][0]['rows']
        self.assertEqual(sum(float(r['debit']) for r in state),oracle['state_debit'])
        self.assertEqual(sum(float(r['credit']) for r in state),oracle['state_credit'])
        works=pack['annexes'][4]['rows'][0]
        for key,value in oracle['pending'].items():self.assertEqual(works[key],value)
        rows=regularization_data(self.year)['rows']
        self.assertEqual({r['lot_number']:r['adjustment'] for r in rows},oracle['adjustments'])
        self.assertTrue(all(c['ok'] for c in pack['checks']))
        current=review.source('accounting',self.year.pk)
        self.assertTrue(render(current,'annexes').startswith(b'%PDF'))

    def test_human_declaration_required_checklist_and_proof_integrity(self):
        data=self.data();data['declaration_confirmed']=False;self.post(data,400)
        data=self.data();data['checks'].pop('works');self.post(data,400)
        data=self.data();data['reviewed_on']='2026-10-16';self.post(data,400)
        data=self.data();data['checks']['unknown']=True;self.post(data,400)
        self.proof.document.archived=True;self.proof.document.save();self.post(self.data(),400)
        self.assertFalse(DossierReview.objects.exists())

    def test_current_approval_official_export_then_stale_on_same_balance_journal_change(self):
        self.post(self.data())
        self.assertEqual(DossierReview.objects.get().kind,'accounting')
        url=self.url+'export/annexes/?official=1'
        self.assertEqual(self.client.get(url).status_code,200)
        before=review.source('accounting',self.year.pk)['source_hash']
        with transaction.atomic():
            self.year.refresh_from_db()
            post_entry(self.year,date(2025,7,1),'OD','Virement neutre',[{'code':'512','debit':'10'},{'code':'512','credit':'10'}],self.user)
        self.assertNotEqual(before,review.source('accounting',self.year.pk)['source_hash'])
        self.assertEqual(self.client.get(self.url).json()['status'],'stale')
        self.assertEqual(self.client.get(url).status_code,400)
        self.assertEqual(self.client.get(self.url+'export/annexes/').status_code,200)
        self.assertEqual(DossierReview.objects.count(),1)

    def test_tampered_proof_and_new_export_model_invalidate_approval(self):
        self.post(self.data())
        with patch.object(review,'EXPORT_VERSION','future-version'):
            self.assertEqual(review.state(review.source('accounting',self.year.pk))[0],'stale')
        with self.proof.file.open('wb') as stream:stream.write(b'changed')
        self.assertEqual(self.client.get(self.url).json()['status'],'stale')
        self.assertEqual(self.client.get(self.url+'export/annexes/?official=1').status_code,400)

    def test_rejected_withdrawn_and_idempotent_history(self):
        from uuid import uuid4
        data=self.data();data['request_id']=str(uuid4())
        self.post(data);self.post(data)
        self.assertEqual(DossierReview.objects.count(),1)
        data=self.data();data['verdict']='rejected';self.post(data)
        self.assertEqual(self.client.get(self.url).json()['status'],'rejected')
        data=self.data();data['verdict']='withdrawn';self.post(data)
        self.assertEqual(self.client.get(self.url).json()['status'],'withdrawn')
        self.assertEqual(DossierReview.objects.count(),3)
        self.assertEqual(self.client.get(self.url+'export/annexes/?official=1').status_code,400)

    def test_private_dossier_and_only_authorized_reviewer(self):
        outsider=Client();outsider.force_login(get_user_model().objects.create_user('outsider'))
        self.assertEqual(outsider.get(self.url).status_code,403)
        self.post(self.data(),403,client=outsider)
        controller=get_user_model().objects.create_user('controller')
        Mandate.objects.create(user=controller,role='controller',starts_on=date(2026,1,1),ends_on=date(2026,12,31),authority='ag',reference='Contrôle',proof=self.proof,created_by=self.user)
        outsider.force_login(controller)
        self.assertTrue(outsider.get(self.url).json()['can_review'])
        self.post(self.data(),client=outsider)

    def test_missing_identity_exceptional_accounts_and_legacy_closure_block_official(self):
        Organization.objects.filter(pk=1).update(address='')
        self.post(self.data(),400)
        Organization.objects.filter(pk=1).update(address='Adresse fictive')
        Account.objects.create(code='164',name='Emprunt collectif — exemple')
        with transaction.atomic():post_entry(self.year,date(2025,1,1),'AN','Emprunt',[{'code':'512','debit':'100'},{'code':'164','credit':'100'}],self.user,kind='opening')
        self.assertTrue(any('Emprunt' in e for e in review.source('accounting',self.year.pk)['errors']))
        self.post(self.data(),400)
        old=annexes(self.year);old['regulatory']['version']='old'
        YearClosure.objects.create(year=self.year,next_year=self.next,snapshot=old,digest='a'*64,closed_by=self.user)
        before=YearClosure.objects.get().snapshot
        self.post(self.data(),400)
        self.assertEqual(YearClosure.objects.get().snapshot,before)

    def assembly(self,long=False):
        meeting=Meeting.objects.create(title='AG fictive',scheduled_at=datetime(2026,12,15,17,tzinfo=dt_timezone.utc),location='Salle commune',created_by=self.user)
        resolution={'id':1,'position':1,'title':'Travaux & entretien <collectif>','majority':'24','text':('Une résolution détaillée. '*500 if long else 'Résolution fictive.'),'pieces':[]}
        packet={'title':meeting.title,'scheduled_at':meeting.scheduled_at.isoformat(),'location':meeting.location,'organizer':'Syndic bénévole','building_address':'12 rue des Tilleuls, 59000 Lille','return_address':'Adresse du syndic','return_email':'syndic@example.test','consultation':'Sur rendez-vous','correspondence_deadline':'2026-12-11','resolutions':[resolution],'electors':[{'elector':'owner:1','name':'Alice Martin','address':'Adresse fictive','lots':['A'],'shares':'600'}]}
        return AssemblyWorkflow.objects.create(meeting=meeting,packet=packet,phase='convened')

    def test_ag_required_fields_all_documents_and_long_resolution(self):
        workflow=self.assembly(long=True)
        url=f'/api/documents/validation/assembly/{workflow.meeting_id}/'
        current=review.source('assembly',workflow.meeting_id)
        self.assertEqual(current['errors'],[])
        for document in ['invitation','correspondence','power']:self.assertTrue(render(current,document).startswith(b'%PDF'))
        self.post(self.data('assembly',workflow.meeting_id),url=url)
        self.assertEqual(self.client.get(url+'export/correspondence/?official=1').status_code,200)
        workflow.packet['return_email']='invalid';workflow.save()
        self.assertEqual(self.client.get(url+'export/correspondence/?official=1').status_code,400)
        workflow.packet.pop('building_address');workflow.save()
        self.assertTrue(any('immeubles' in e for e in review.source('assembly',workflow.meeting_id)['errors']))

    def test_votes_and_attendance_change_invalidate_minutes_review(self):
        workflow=self.assembly()
        workflow.minutes={'resolutions':[{'resolution':workflow.packet['resolutions'][0],'votes':[{'tour':1,'amendment':'','result':{'rule':'24','for_votes':'600','against_votes':'0','abstain_votes':'0','explanation':'Majorité acquise.'}}],'adopted':True,'groups':{'against':[],'abstain':[],'deemed_default':[]}}],'bureau':{'president':'Alice','secretary':'Benoît'},'appeal_notice':'Rappel de recours fictif'}
        workflow.save()
        current=review.source('minutes',workflow.meeting_id)
        for document in ['minutes','attendance']:self.assertTrue(render(current,document).startswith(b'%PDF'))
        self.post(self.data('minutes',workflow.meeting_id),url=f'/api/documents/validation/minutes/{workflow.meeting_id}/')
        workflow.participants=[{'elector':'owner:1','attendance':'present'}];workflow.save()
        self.assertEqual(review.state(review.source('minutes',workflow.meeting_id))[0],'stale')

    def test_completed_work_keeps_three_financing_accounts_out_of_current_charges(self):
        project=FinanceProject.objects.create(name='Façade',key=self.key,budget=300,decision='AG',decided_on=date(2025,1,1))
        with transaction.atomic():
            post_entry(self.year,date(2025,1,1),'AN','Soldes repris',[{'code':'512','debit':'100'},{'code':'105','owner':self.owner,'lot':self.lot,'credit':'80'},{'code':'1032','owner':self.owner,'lot':self.lot,'credit':'20'}],self.user,kind='opening')
            call=FundCall.objects.create(year=self.year,key=self.key,project=project,label='Travaux',date=date(2025,2,1),due_date=date(2025,2,1),amount=200,kind='works',decision='AG')
            publish_call(call,self.user);self.year.refresh_from_db()
            post_entry(self.year,date(2025,3,1),'OD','Fonds affecté',[{'code':'105','owner':self.owner,'lot':self.lot,'project':project,'debit':'80'},{'code':'102','project':project,'credit':'80'}],self.user)
            post_entry(self.year,date(2025,3,1),'OD','PPT affecté',[{'code':'1032','owner':self.owner,'lot':self.lot,'project':project,'debit':'20'},{'code':'102','project':project,'credit':'20'}],self.user,kind='advance-use')
            record_expense(dict(year=self.year.pk,key=self.key.pk,project=project.pk,supplier='Entreprise',reference='Façade',label='Travaux',date='2025-04-01',amount='300'),self.user)
            self.year.refresh_from_db();finish_project(project,self.year,{'date':'2025-05-01','decision':'AG de réception'},self.user)
        pack=annexes(self.year)['regulatory']
        amounts={r['code']:r['actual_current'] for r in pack['annexes'][1]['rows'] if r['activity']=='Travaux terminés'}
        self.assertEqual({k:amounts[k] for k in ['671','702','703','705']},{'671':'300.00','702':'200.00','703':'20.00','705':'80.00'})
        self.assertEqual(regularization_data(self.year)['rows'],[])
        self.assertEqual(pack['errors'],[])

    def test_prior_year_work_restored_to_its_actual_account_not_671(self):
        from finance.cycle import digest
        project=FinanceProject.objects.create(name='Étude technique',key=self.key,budget=500,decision='AG',decided_on=date(2025,1,1))
        with transaction.atomic():
            call=FundCall.objects.create(year=self.year,key=self.key,project=project,label='Étude',date=date(2025,2,1),due_date=date(2025,2,1),amount=500,kind='works',decision='AG')
            publish_call(call,self.user)
            record_expense(dict(year=self.year.pk,key=self.key.pk,project=project.pk,supplier='Architecte',reference='Étude',label='Étude votée',date='2025-04-01',amount='300',charge_code='672'),self.user)
            self.year.refresh_from_db();close_year(self.year,self.next,{'source_hash':digest(annexes(self.year))},self.user)
            self.next.refresh_from_db();finish_project(project,self.next,{'date':'2026-06-01','decision':'AG de réception'},self.user)
        pack=annexes(self.next)['regulatory']
        charges=[r for r in pack['annexes'][1]['rows'] if r['side']=='Charges' and r['activity']=='Travaux terminés']
        self.assertEqual(next(r for r in charges if r['code']=='672')['actual_current'],'300.00')
        self.assertEqual(next(r for r in charges if r['code']=='671')['actual_current'],'0.00')
        self.assertEqual(pack['errors'],[])

    def test_negative_waiting_and_bank_overdraft_preserve_signs_and_reversal(self):
        project=self.representative()
        with transaction.atomic():
            self.year.refresh_from_db()
            original=post_entry(self.year,date(2025,8,1),'BQ','Acompte travaux',[{'code':'401','project':project,'debit':'100'},{'code':'512','project':project,'credit':'100'}],self.user)
            post_entry(self.year,date(2025,9,1),'BQ','Annulation acompte',[{'code':'401','project':project,'credit':'100'},{'code':'512','project':project,'debit':'100'}],self.user,reversal_of=original)
        pack=annexes(self.year)['regulatory']
        self.assertEqual(pack['annexes'][4]['rows'][0]['paid'],'0.00')
        with transaction.atomic():
            self.year.refresh_from_db()
            record_expense(dict(year=self.year.pk,key=self.key.pk,project=project.pk,supplier='Entreprise',reference='Complément',label='Complément',date='2025-09-10',amount='400'),self.user)
            self.year.refresh_from_db()
            post_entry(self.year,date(2025,9,15),'BQ','Paiement travaux',[{'code':'401','project':project,'debit':'150'},{'code':'512','project':project,'credit':'150'}],self.user)
            post_entry(self.year,date(2025,9,20),'BQ','Versement propriétaire pour les travaux',[{'code':'512','project':project,'debit':'50'},{'code':'450','project':project,'owner':self.owner,'credit':'50'}],self.user)
        pack=annexes(self.year)['regulatory']
        self.assertEqual(pack['annexes'][4]['rows'][0]['waiting'],'-200.00')
        self.assertEqual(pack['annexes'][4]['rows'][0]['paid'],'150.00')
        self.assertEqual(next(r for r in pack['annexes'][0]['rows'] if r['code']=='512')['credit'],'100.00')
        self.assertEqual(pack['errors'],[])

    def test_delegation_and_ambiguous_budget_block_review(self):
        with transaction.atomic():post_entry(self.year,date(2025,1,1),'AN','Délégation',[{'code':'512','debit':'100'},{'code':'106','credit':'100'}],self.user,kind='opening')
        code=Account.objects.create(code='601',name='Eau')
        Budget.objects.create(year=self.year,account=code,amount=100)
        Budget.objects.create(year=self.year,account=code,key=self.key,amount=100)
        errors=review.source('accounting',self.year.pk)['errors']
        self.assertTrue(any('Délégation' in e for e in errors))
        self.assertTrue(any('budget global' in e for e in errors))
        self.post(self.data(),400)

    def test_accruals_and_prepaid_expenses_use_only_current_year_charges(self):
        Account.objects.create(code='408',name='Factures non parvenues')
        Account.objects.create(code='486',name='Charges constatées d’avance')
        with transaction.atomic():
            post_entry(self.year,date(2025,12,31),'OD','Facture non parvenue',[{'code':'601','key':self.key,'debit':'100'},{'code':'408','credit':'100'}],self.user)
            post_entry(self.year,date(2025,12,31),'OD','Part à reporter',[{'code':'486','debit':'50'},{'code':'601','key':self.key,'credit':'50'}],self.user)
        pack=annexes(self.year)['regulatory']
        self.assertEqual(pack['errors'],[])
        self.assertEqual(next(r for r in pack['annexes'][2]['rows'] if r['code']=='601')['actual_current'],'50.00')
        self.assertEqual(sum(float(r['adjustment']) for r in regularization_data(self.year)['rows']),50)

    def test_three_reference_documents_render_from_fictitious_sources(self):
        import os
        self.representative()
        annual=review.source('accounting',self.year.pk)
        workflow=self.assembly(long=True)
        correspondence=review.source('assembly',workflow.meeting_id)
        workflow.minutes={'resolutions':[{'resolution':workflow.packet['resolutions'][0],'votes':[{'tour':1,'amendment':'','result':{'rule':'24','for_votes':'600','against_votes':'0','abstain_votes':'400','explanation':'Exemple fictif de majorité exprimée.'},'incident':'Réserve fictive à conserver intégralement.'}],'adopted':True,'groups':{'against':[],'abstain':[{'name':'Benoît Petit','shares':'400'}],'deemed_default':[]}}],'bureau':{'president':'Alice Martin','secretary':'Benoît Petit','scrutineers':'Camille Durand'},'appeal_notice':'Article 42, alinéa 2 : délai de deux mois à compter de la notification du procès-verbal, sans ses annexes. Notification par le syndic dans le mois de l’assemblée. Exemple fictif.', 'remarks':'Dossier de démonstration, aucune décision réelle.'}
        workflow.save()
        samples=[('01-annexes-fictives.pdf',annual,'annexes'),('02-correspondance-fictive.pdf',correspondence,'correspondence'),('03-pv-fictif.pdf',review.source('minutes',workflow.meeting_id),'minutes')]
        destination=os.environ.get('COPRO_REVIEW_OUTPUT')
        if destination:Path(destination).mkdir(parents=True,exist_ok=True)
        for name,current,document in samples:
            content=render(current,document)
            self.assertGreater(len(content),10000)
            if destination:(Path(destination)/name).write_bytes(content)

    def test_invitation_requires_current_accounting_review_and_its_decision(self):
        workflow=self.assembly()
        workflow.packet['account_year']={'id':self.year.pk,'dossier':annexes(self.year)['regulatory']};workflow.save()
        url=f'/api/documents/validation/assembly/{workflow.meeting_id}/'
        self.post(self.data('assembly',workflow.meeting_id),400,url=url)
        self.post(self.data())
        self.post(self.data('assembly',workflow.meeting_id),url=url)
        self.assertEqual(review.state(review.source('assembly',workflow.meeting_id))[0],'approved')
        data=self.data();data['verdict']='withdrawn';self.post(data)
        self.assertEqual(review.state(review.source('assembly',workflow.meeting_id))[0],'stale')
        self.post(self.data())
        self.assertEqual(review.state(review.source('assembly',workflow.meeting_id))[0],'stale')

