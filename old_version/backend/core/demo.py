"""Explicit CLI-only, fictitious lifecycle. Never imported by the web routes.

Requires an instance without journal entries. Existing contacts/lots are retained;
the special key excludes them from every demo charge. Only this process uses a
historical clock to exercise historical AG steps. No message or payment is sent.
"""
from contextlib import contextmanager
from datetime import date, datetime, time
from decimal import Decimal
from io import BytesIO, StringIO
import csv
import hashlib
from unittest.mock import patch
from zoneinfo import ZoneInfo
from django.core.files.base import ContentFile
from django.db.models import Sum, F
from django.utils import timezone
from core.models import Owner, Lot
from core.access import provision_access
from documents.models import Document, Version, Folder
from finance.models import (Account, BankAccount, FiscalYear, ChargeKey, Share,
    FundCall, Budget, Receipt, Line, Entry, BankTransfer, FundingPolicy, AuditEvent,
    Expense, ExpensePayment, YearClosure, FinanceProject)
from finance.services import post_entry, publish_call, record_expense, pay_expense
from finance.cycle import (annexes, digest, close_year, regularization_data,
    match_lines, line_remaining, close_checks)
from finance.reconciliation import import_statement, match_bank, validate_statement, bank_balance
from governance.models import Meeting, Resolution, AssemblyWorkflow, AssemblyVote, AssemblyDecision
from governance import workflow as ag
from governance.workflow_views import execute_decision
from governance.templates import TEMPLATES
from operations.models import Supplier

AS_OF=date(2026,10,15)
TAG='[DÉMO]'
MARKER='demo.lifecycle.v1'
KEY=TAG+' Lots fictifs uniquement'
PEOPLE=[('Alice','Martin',300,'Mensuel'),('Bruno','Petit',250,'Trimestriel'),
        ('Chloé','Bernard',200,'Annuel anticipé'),('David','Leroy',150,'Paiement partiel'),
        ('Emma','Roux',100,'Impayé')]
EXPECTED={'Alice':'300.00','Bruno':'-250.00','Chloé':'-200.00','David':'1890.00','Emma':'1360.00'}


@contextmanager
def historical(day):
    """Local to the seed process; gunicorn and the machine clock are untouched."""
    now=datetime.combine(day,time(12),ZoneInfo('Europe/Paris'))
    with patch('django.utils.timezone.localdate',return_value=day),patch('django.utils.timezone.now',return_value=now):
        yield


def money(value):return str(Decimal(value).quantize(Decimal('.01')))


def inspect_demo():
    key=ChargeKey.objects.get(name=KEY)
    old=FiscalYear.objects.get(name=TAG+' 2025 — exercice terminé')
    current=FiscalYear.objects.get(starts_on=date(2026,1,1),ends_on=date(2026,12,31))
    owners=list(Owner.objects.filter(pk__in=key.shares.values('lot__owner_id')).order_by('id'))
    rows=[]
    for first,last,weight,rhythm in PEOPLE:
        owner=next(o for o in owners if o.email==first.casefold().replace('é','e')+'.demo@copro.example.test')
        amount=Line.objects.filter(entry__year=current,owner=owner,account__code='450').aggregate(d=Sum('debit'),c=Sum('credit'))
        balance=(amount['d'] or 0)-(amount['c'] or 0)
        rows.append({'owner':owner.pk,'name':str(owner),'rhythm':rhythm,'balance':money(balance),'expected':EXPECTED[first]})
    banks=list(BankAccount.objects.filter(name__startswith=TAG).select_related('account'))
    accounts=[{'id':b.pk,'name':b.name,'balance':money(bank_balance(b,AS_OF))} for b in banks]
    unpaid=sum((e.amount-sum((p.amount for p in e.payments.all()),Decimal('0')) for e in Expense.objects.filter(year=current,key=key)),Decimal('0'))
    pack=annexes(current)['regulatory']
    project=FinanceProject.objects.get(name=TAG+' Réfection du portail')
    work=next(r for r in pack['annexes'][4]['rows'] if r['id']==project.pk)
    checks=[{'label':'Journaux équilibrés écriture par écriture','ok':not Entry.objects.annotate(d=Sum('lines__debit'),c=Sum('lines__credit')).exclude(d=F('c')).exists()},
        {'label':'Exercice 2025 clôturé et reporté','ok':YearClosure.objects.filter(year=old,next_year=current).exists()},
        {'label':'Soldes des cinq copropriétaires conformes','ok':all(r['balance']==r['expected'] for r in rows)},
        {'label':'Banque courante 4 050 € / fonds travaux 450 €','ok':sorted(b['balance'] for b in accounts)==['4050.00','450.00']},
        {'label':'Factures restant dues : 1 800 €','ok':unpaid==1800},
        {'label':'Travaux : appelés 2 000 €, réalisés/payés 1 200 €, attente 800 €','ok':(work['funding'],work['expenses'],work['paid'],work['waiting'])==('2000.00','1200.00','1200.00','800.00')},
        {'label':'Concordances des annexes 2026','ok':not pack['errors'] and all(c['ok'] for c in pack['checks'])},
        {'label':'AG historique archivée avec votes et PV','ok':AssemblyWorkflow.objects.filter(meeting__title=TAG+' AG du 14 mars 2026 — simulation terminée',phase='closed').exists()}]
    return {'scenario':MARKER,'as_of':str(AS_OF),'fictitious':True,'year':current.pk,'year_name':current.name,'previous_year':old.pk,
        'key':key.pk,'owners':rows,'banks':accounts,'unpaid_invoices':money(unpaid),'work':{k:work[k] for k in ['project','funding','expenses','paid','waiting']},
        'checks':checks,'meetings':list(Meeting.objects.filter(title__startswith=TAG).values('id','title','archived')),
        'calls':FundCall.objects.filter(key=key).count(),'entries':Entry.objects.count(),'documents':Document.objects.filter(title__startswith=TAG).count()}


class DemoScenario:
    def __init__(self,user):
        self.user=user;self.files=[];self.people=[]

    def cleanup_files(self):
        for storage,name in self.files:storage.delete(name)

    def document(self,title,paragraphs=None,content=None):
        from documents.pdf import p, SimpleDocTemplate, A4
        if content is None:
            stream=BytesIO();pdf=SimpleDocTemplate(stream,pagesize=A4,leftMargin=40,rightMargin=40,topMargin=40,bottomMargin=40)
            story=[p('DÉMONSTRATION — SANS VALEUR OFFICIELLE','Heading1'),p(title,'Heading2'),
                p('Données fictives. Aucun envoi, règlement bancaire ou acte signé réel. Les preuves et signatures sont simulées pour tester le parcours.')]
            story += [p(text) for text in paragraphs or []]
            pdf.build(story);content=stream.getvalue()
        doc=Document.objects.create(title=TAG+' '+title,folder=self.folder,published=False)
        version=Version(document=doc,filename='DEMO-document.pdf',size=len(content),content_type='application/pdf',checksum=hashlib.sha256(content).hexdigest(),created_by=self.user)
        version.file.save('demo.pdf',ContentFile(content),save=False);self.files.append((version.file.storage,version.file.name));version.save()
        doc.current=version;doc.save(update_fields=['current'])
        return version

    def post(self,year,day,label,rows,**kw):
        year.refresh_from_db()
        return post_entry(year,day,'BQ' if any(str(r['code']).startswith('512') for r in rows) else 'OD',TAG+' '+label,rows,self.user,reference=TAG+' simulation',**kw)

    def call(self,year,day,value,kind='current',project=None,label='Provisions courantes'):
        call=FundCall.objects.create(year=year,key=self.key,label=TAG+' '+label,date=day,due_date=day,amount=value,kind=kind,project=project,decision=TAG+' décision fictive')
        publish_call(call,self.user);return call

    def match_current_credits(self,year):
        for owner in self.people:
            debits=Line.objects.filter(entry__year=year,owner=owner,debit__gt=0,entry__fundcall__kind='current').order_by('entry__date','id')
            credits=Line.objects.filter(owner=owner,account__code='450',credit__gt=0,entry__date__lte=AS_OF).exclude(entry__kind__in=['carry','closing']).order_by('entry__date','id')
            for debit in debits:
                for credit in credits:
                    value=min(line_remaining(debit),line_remaining(credit))
                    if value:match_lines(debit,credit,value,self.user)

    def receive(self,year,owner,day,value,call=None):
        entry=self.post(year,day,'Versement '+str(owner),[{'code':self.bank.account.code,'debit':value},{'code':'450','owner':owner,'credit':value}])
        Receipt.objects.create(owner=owner,amount=value,entry=entry,bank=self.bank)
        if call:
            match_lines(call.entry.lines.get(owner=owner,account__code='450'),entry.lines.get(account__code='450'),Decimal(str(value)),self.user)

    def invoice(self,year,code,value,day,label,paid=None,project=None):
        supplier=Supplier.objects.create(name=TAG+' '+label,trade=TAG+' fournisseur fictif',created_by=self.user)
        proof=self.document('Facture '+label+' '+str(year.starts_on.year),['Référence DEMO-'+code+'-'+str(year.starts_on.year),'Montant : '+money(value)+' €','Date : '+str(day),'Objet : '+label])
        expense=record_expense({'year':year.pk,'key':self.key.pk,'supplier_record':supplier.pk,'document':proof.document_id,
            'reference':'DEMO-'+code+'-'+str(year.starts_on.year),'label':TAG+' '+label,'date':str(day),'amount':str(value),
            'charge_code':code,**({'project':project.pk} if project else {})},self.user)
        if paid:pay_expense(expense,day,Decimal(str(paid)),self.user,self.bank.pk)
        return expense

    def statement(self,bank,year,end,opening):
        lines=list(Line.objects.filter(account=bank.account,entry__year=year,entry__date__lte=end).exclude(entry__kind__in=['opening','carry','closing']).select_related('entry').order_by('entry__date','id'))
        stream=StringIO();writer=csv.writer(stream,delimiter=';');writer.writerow(['date','libelle','montant','reference'])
        for line in lines:writer.writerow([str(line.entry.date),line.entry.label,money(line.debit-line.credit),'DEMO-'+str(line.pk)])
        closing=Decimal(str(opening))+sum((l.debit-l.credit for l in lines),Decimal('0'))
        statement,_=import_statement({'bank':bank.pk,'starts_on':str(year.starts_on),'ends_on':str(end),'opening_balance':str(opening),'closing_balance':str(closing),'csv':stream.getvalue()},self.user)
        for row,line in zip(statement.rows.order_by('id'),lines):match_bank(row,[line.pk],self.user)
        validate_statement(statement,self.user)
        return statement

    def assembly(self,year,proof,training=False):
        day=AS_OF if training else date(2026,3,14)
        title=TAG+(' AG d’entraînement — à terminer' if training else ' AG du 14 mars 2026 — simulation terminée')
        # Existing lot holders remain electors but receive no demo allocation.
        owners=list(Owner.objects.filter(lots__shares__gt=0).distinct())
        meeting=Meeting.objects.create(title=title,scheduled_at=datetime.combine(day,time(18),ZoneInfo('Europe/Paris')),location=TAG+' Salle commune fictive',created_by=self.user,
            notes='SIMULATION SANS VALEUR OFFICIELLE. Aucune notification ni signature réelle.',
            roster=[{'owner_id':o.pk,'name':str(o),'shares':str(sum(o.lots.values_list('shares',flat=True))),'attendance':'absent'} for o in owners])
        specs=[('Choix d’un prestataire fictif','L’assemblée choisit le devis fictif A pour comparaison et entraînement.','24',''),
               ('Travaux fictifs à majorité absolue','L’assemblée examine une amélioration fictive de 2 000 euros.','25','')] if training else [
            ('Approbation des comptes','L’assemblée approuve, uniquement dans cette simulation, les comptes fictifs 2025 : 12 000 euros de provisions, 11 000 euros de charges et 1 000 euros d’excédent à répartir.','24','accounts'),
            ('Actualisation du budget 2026','Le budget fictif 2026 est fixé à 12 000 euros, selon le comparatif joint.','24','budget'),
            ('Provisions restantes 2026','Après les 3 000 euros du premier trimestre, l’assemblée fixe les trois appels fictifs restants à 3 000 euros chacun, exigibles les 1er avril, juillet et octobre 2026.','24',''),
            ('Réfection du portail','L’assemblée décide des travaux fictifs de conservation du portail pour un plafond de 2 000 euros, financés par les seuls lots DÉMO, exigibles le 15 avril 2026.','24','')]
        settings={};resolutions=[]
        for i,(name,text,majority,template) in enumerate(specs,1):
            res=Resolution.objects.create(meeting=meeting,position=i,title=(name if template=='accounts' else TAG+' '+name),text=text,majority=majority);resolutions.append(res)
            required=next((t['pieces'] for t in TEMPLATES if t['id']==template),[])
            settings[str(res.pk)]={'template':template,'key':self.key.pk,'key_confirmed':True,'pieces':[{'label':label,'version':self.annual.pk if label.startswith(('Annexe','Projet d’état')) else proof.pk} for label in required]}
        workflow=AssemblyWorkflow.objects.create(meeting=meeting,config={'organizer':TAG+' Syndic fictif','building_address':TAG+' 12 rue Exemple, 59000 Lille',
            'return_address':TAG+' Adresse fictive du syndic','return_email':'syndic.demo@copro.example.test','consultation':TAG+' Consultation fictive sur rendez-vous les 9 et 10 mars ; documents sans valeur officielle.',
            'legal_checked':True,'fiscal_year':year.pk,'accounts_reviewed':True,'accounts_source_hash':annexes(year)['regulatory']['source_hash'],
            'contacts':{f'owner:{o.pk}':{'address':TAG+' Adresse fictive pour simulation'} for o in owners},'resolutions':settings})
        frozen=date(2026,9,1) if training else date(2026,2,1)
        with historical(frozen):ag.freeze(workflow,self.user)
        with historical(frozen):
            for elector in workflow.packet['electors']:ag.register_delivery(workflow,self.user,{'kind':'invitation','elector':elector['elector'],'method':'lrar','sent_on':str(frozen),'effective_on':str(frozen),'proof':proof.pk,'proof_checked':True,'reference':TAG+' PREUVE SIMULÉE — AUCUN ENVOI'})
        if training:return workflow
        with historical(day):
            participants=[]
            for elector in workflow.packet['electors']:
                owner_id=elector['owner_id'];row={'elector':elector['elector'],'attendance':'absent'}
                if owner_id in [o.pk for o in self.people[:3]]:row['attendance']='present'
                elif owner_id==self.people[3].pk:
                    row.update(attendance='correspondence',received_on='2026-03-09',proof=proof.pk,choices={str(r.pk):'for' for r in resolutions})
                participants.append(row)
            ag.set_participants(workflow,self.user,{'participants':participants})
            ag.start_session(workflow,self.user,{'president':f'owner:{self.people[0].pk}','secretary':str(self.people[1]),'scrutineers':str(self.people[2]),'attendance_checked':True,'president_eligible':True,'bureau_elected':True})
            for res in resolutions:ag.record_vote(workflow,self.user,{'resolution':res.pk,'choices':{f'owner:{o.pk}':('against' if o==self.people[2] and res.position==4 else 'for') for o in self.people[:3]}})
            ag.prepare_minutes(workflow,self.user,{'reviewed':True,'remarks':'DÉMONSTRATION : toutes les décisions, preuves et signatures sont fictives.'})
            from documents.review import source
            from documents.pdf import render
            self.document('Convocation fictive',content=render(source('assembly',meeting.pk),'invitation'))
            self.document('Formulaire fictif',content=render(source('assembly',meeting.pk),'correspondence'))
            pv=self.document('PV fictif — signatures simulées',content=render(source('minutes',meeting.pk),'minutes'))
            presence=self.document('Présence fictive — signatures simulées',content=render(source('minutes',meeting.pk),'attendance'))
            ag.sign_minutes(workflow,self.user,{'signed_on':str(day),'signed_proof':pv.pk,'attendance_proof':presence.pk,'signatures_checked':True})
            for elector in workflow.minutes['required_notifications']:ag.register_delivery(workflow,self.user,{'kind':'minutes','elector':elector,'method':'lrar','sent_on':str(day),'effective_on':str(day),'proof':proof.pk,'proof_checked':True,'reference':TAG+' NOTIFICATION SIMULÉE — AUCUN ENVOI'})
            votes={v.resolution_id:v for v in workflow.votes.all()}
            execute_decision(workflow,self.user,{'kind':'accounts','vote':votes[resolutions[0].pk].pk,'year':year.pk,'source_hash':regularization_data(year,day)['source_hash'],'reviewed':True})
            execute_decision(workflow,self.user,{'kind':'budget','vote':votes[resolutions[1].pk].pk,'year':self.current.pk,'reviewed':True,
                'lines':[{'code':code,'key':self.key.pk,'amount':value} for code,value in [('601','2400'),('602','1200'),('615','4000'),('616','2000'),('614','2400')]]})
            execute_decision(workflow,self.user,{'kind':'current','vote':votes[resolutions[2].pk].pk,'year':self.current.pk,'key':self.key.pk,'label':TAG+' Charges courantes 2026','amount':'9000','date':'2026-04-01','count':3,'months':3,'reviewed':True})
            execute_decision(workflow,self.user,{'kind':'works','vote':votes[resolutions[3].pk].pk,'year':self.current.pk,'key':self.key.pk,'label':TAG+' Réfection du portail','amount':'2000','date':'2026-04-15','count':1,'months':3,'reviewed':True})
            ag.close_assembly(workflow,self.user,{'reviewed':True})
        return workflow

    def run(self,with_access=False):
        if AuditEvent.objects.filter(action=MARKER).exists():return inspect_demo(),[],False
        if timezone.localdate()<AS_OF:raise ValueError('Ce jeu de démonstration nécessite une date réelle au moins égale au 15 octobre 2026.')
        if Entry.objects.exists():raise ValueError('La simulation initiale exige une instance sans écriture comptable ; aucune donnée existante n’a été modifiée.')
        if ChargeKey.objects.filter(name=KEY).exists() or Owner.objects.filter(email__endswith='.demo@copro.example.test').exists():raise ValueError('Des données DÉMO existent sans marqueur de scénario complet ; contrôlez-les avant une nouvelle importation.')
        if FiscalYear.objects.filter(starts_on__lte=date(2025,12,31),ends_on__gte=date(2025,1,1)).exists():raise ValueError('La période 2025 existe déjà : ne pas l’écraser.')
        existing=FiscalYear.objects.filter(starts_on__lte=date(2026,12,31),ends_on__gte=date(2026,1,1))
        if existing.exists() and (existing.count()!=1 or not existing.filter(starts_on=date(2026,1,1),ends_on=date(2026,12,31),closed=False).exists()):raise ValueError('L’exercice 2026 existant ne permet pas ce scénario ; aucune réécriture.')
        self.current=existing.first() or FiscalYear.objects.create(name=TAG+' 2026 — année en cours',starts_on=date(2026,1,1),ends_on=date(2026,12,31))
        if FundingPolicy.objects.filter(year=self.current).exists():raise ValueError('Un paramétrage de financement 2026 existe déjà ; ne pas le remplacer par celui de la démo.')
        old=FiscalYear.objects.create(name=TAG+' 2025 — exercice terminé',starts_on=date(2025,1,1),ends_on=date(2025,12,31))
        self.folder=Folder.objects.get_or_create(name=TAG+' Simulation de la copropriété')[0]
        self.key=ChargeKey.objects.create(name=KEY,general=False,annual_budget=12000)
        credentials=[]
        for i,(first,last,weight,rhythm) in enumerate(PEOPLE,1):
            owner=Owner.objects.create(first_name=TAG+' '+first,last_name=last,email=first.casefold().replace('é','e')+'.demo@copro.example.test');self.people.append(owner)
            lot=Lot.objects.create(number='DEMO-A'+str(i),owner=owner,shares=weight,area=40+i*10,floor=str(i))
            Share.objects.create(key=self.key,lot=lot,value=weight)
            if with_access:credentials.append({'name':str(owner),**provision_access(owner)})
        # A second lot illustrates aggregation of several lots for one owner.
        lot=Lot.objects.get(number='DEMO-A3');lot.shares=180;lot.save();Share.objects.filter(key=self.key,lot=lot).update(value=180)
        parking=Lot.objects.create(number='DEMO-P3',owner=self.people[2],shares=20,kind='parking');Share.objects.create(key=self.key,lot=parking,value=20)
        for code in ['512991','512992']:
            if Account.objects.filter(code=code).exists():raise ValueError('Un compte réservé à la démo est déjà utilisé.')
        self.bank=BankAccount.objects.create(name=TAG+' Compte courant fictif',account=Account.objects.create(code='512991',name=TAG+' Banque courante'),is_default=not BankAccount.objects.filter(is_default=True).exists())
        self.fund_bank=BankAccount.objects.create(name=TAG+' Fonds travaux fictif',kind='works',account=Account.objects.create(code='512992',name=TAG+' Banque fonds travaux'))
        for month in [1,4,7,10]:self.call(old,date(2025,month,1),3000,label='Charges courantes 2025 T'+str((month-1)//3+1))
        for owner,(_,_,weight,_) in zip(self.people,PEOPLE):
            for month in [1,4,7,10]:self.receive(old,owner,date(2025,month,5),Decimal(3)*weight)
        self.match_current_credits(old)
        for code,value,label,month,budget in [('601',2400,'Eau',4,2600),('602',1200,'Électricité',5,1400),('615',3600,'Nettoyage',11,4000),('616',1800,'Assurance',7,2000),('614',2000,'Entretien',12,2000)]:
            self.invoice(old,code,value,date(2025,month,10),label,paid=value)
            account=Account.objects.get(code=code);Budget.objects.create(year=old,account=account,key=self.key,amount=budget)
        self.statement(self.bank,old,old.ends_on,0)
        proof=self.document('Budget et preuves simulées',['Aucune preuve de notification ni signature réelle.','Budget 2025 : provisions 12 000 euros ; dépenses 11 000 euros : eau 2 400, électricité 1 200, nettoyage 3 600, assurance 1 800, entretien 2 000.','Budget 2026 : 12 000 euros. Appels T1 : 3 000 euros ; appels T2, T3, T4 : 3 000 euros chacun.','Travaux portail : budget 2 000 euros. Fonds travaux : cotisation fictive 600 euros.','Consultation fictive : sur rendez-vous les 9 et 10 mars 2026, salle DÉMO.'])
        from documents.review import source
        from documents.pdf import render
        self.annual=self.document('Dossier annuel 2025 — projet fictif',content=render(source('accounting',old.pk),'annexes'))
        self.assembly(old,proof)
        old.refresh_from_db();close_year(old,self.current,{'source_hash':digest(annexes(old))},self.user)
        self.current.refresh_from_db()
        FundingPolicy.objects.create(year=self.current,housing='housing',received_on=date(1990,1,1),annual_budget=12000,budget_reference=TAG+' budget fictif',ppt_adopted=False,fund_contribution=600,fund_reference=TAG+' cotisation fictive',fund_proof=proof,updated_by=self.user)
        self.call(self.current,date(2026,1,1),3000,label='Charges courantes 2026 T1')
        for call in FundCall.objects.filter(year=self.current,key=self.key,entry__isnull=True).order_by('date'):publish_call(call,self.user)
        workcall=FundCall.objects.get(year=self.current,key=self.key,kind='works')
        fundcall=self.call(self.current,date(2026,4,15),600,kind='fund',label='Cotisation fonds travaux 2026')
        for month in range(1,11):self.receive(self.current,self.people[0],date(2026,month,10),300)
        for month in [1,4,7,10]:self.receive(self.current,self.people[1],date(2026,month,5),750)
        self.receive(self.current,self.people[2],date(2026,1,5),2400)
        self.receive(self.current,self.people[3],date(2026,2,10),150)
        self.match_current_credits(self.current)
        for owner,(_,_,weight,_) in zip(self.people[:3],PEOPLE):
            self.receive(self.current,owner,date(2026,4,20),Decimal(2)*weight,call=workcall)
            self.receive(self.current,owner,date(2026,4,20),Decimal('.6')*weight,call=fundcall)
        for code,value,day,label,paid in [('616',1900,date(2026,1,15),'Assurance 2026',1900),('601',1800,date(2026,6,15),'Eau 2026',900),('615',3000,date(2026,9,15),'Nettoyage 2026',3000),('602',900,date(2026,8,5),'Électricité 2026',None)]:self.invoice(self.current,code,value,day,label,paid=paid)
        project=FinanceProject.objects.get(name=TAG+' Réfection du portail')
        self.invoice(self.current,'671',1200,date(2026,5,10),'Portail',paid=1200,project=project)
        transfer=self.post(self.current,date(2026,4,21),'Alimentation banque fonds travaux',[{'code':self.fund_bank.account.code,'debit':'450'},{'code':self.bank.account.code,'credit':'450'}])
        BankTransfer.objects.create(source=self.bank,destination=self.fund_bank,amount=450,entry=transfer)
        self.statement(self.bank,self.current,AS_OF,1000);self.statement(self.fund_bank,self.current,AS_OF,0)
        self.assembly(old,proof,training=True)
        report=inspect_demo()
        if not all(c['ok'] for c in report['checks']):raise ValueError('Le scénario a révélé un écart : '+', '.join(c['label'] for c in report['checks'] if not c['ok']))
        self.document('Lire la simulation — soldes et parcours',['Situation fictive au 15 octobre 2026.','Choisir l’exercice 2026 existant : '+self.current.name,'Rapports comptables / Comptes copropriétaires : débit = dû ; crédit = avance/excédent.',
            *[r['name']+' : '+r['rhythm']+' ; solde '+r['balance']+' euros.' for r in report['owners']],
            'Banque courante 4 050 euros ; banque fonds travaux 450 euros. Factures à régler 1 800 euros.',
            'Activer Inclure les archives dans Assemblées générales pour consulter l’AG complète du 14 mars 2026.',
            'Choisir l’AG d’entraînement pour enregistrer les présences, ouvrir la séance et voter. Les invitations sont des preuves simulées, aucun courriel n’a été envoyé.',
            'Ne pas utiliser les documents et décisions DÉMO comme des actes officiels. Aucune validation métier réelle n’a été enregistrée.'])
        AuditEvent.objects.create(actor=self.user,action=MARKER,target='simulation-2025-2026')
        return inspect_demo(),credentials,True
