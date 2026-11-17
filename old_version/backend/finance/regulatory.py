"""Versioned presentation and cross-checks for the five annual statements.

No journal is rewritten by a report. Presentation regroupings are disclosed;
closed dossiers keep their original snapshot, including older report versions.
"""
from collections import defaultdict
from decimal import Decimal
from django.db.models import Q
from .models import Line, FiscalYear, Budget, FinanceProject, AnnualSettlement, Organization, ExpensePayment

ZERO = Decimal('0')
SOURCE = 'https://www.legifrance.gouv.fr/loda/id/LEGITEXT000006051416/'
MODEL_VERSION = '2026.10.2'
WORK_PRODUCTS = {'702','703','704','705','706','712','718','780'}


def m(value):
    return str(value.quantize(Decimal('.01')))


def project_states(year):
    completed, pending = [], []
    for p in FinanceProject.objects.select_related('key').all():
        if p.decided_on and p.decided_on > year.ends_on:
            continue
        lines = list(Line.objects.filter(project=p,entry__date__lte=year.ends_on)
            .exclude(entry__kind__in=['carry','closing']).select_related('account','entry','entry__reversal_of').prefetch_related('entry__lines__account'))
        # Include inverse entries: their accounting date determines the period of correction.
        actual = [l for l in lines if l.account.code.startswith('67') and l.entry.kind!='project-complete']
        provisions = [l for l in lines if l.account.code=='102' and l.entry.kind!='project-complete']
        received = [l for l in lines if l.account.code.startswith('13')]
        receivable = [l for l in lines if l.account.code.startswith('441')]
        cash = [l for l in lines if l.account.code.startswith(('512','514','531'))
                and any(counter.account.code.startswith(('40','67')) for counter in l.entry.lines.all())]
        amount = lambda items, sign=1: sum(((l.debit-l.credit)*sign for l in items),ZERO)
        costs, funding = amount(actual), amount(provisions,-1)
        expenses_by_code = defaultdict(lambda: ZERO)
        for line in actual:
            expenses_by_code[line.account.code] += line.debit-line.credit
        fund_used = sum((l.debit-l.credit for l in lines if l.account.code=='105'),ZERO)
        advance_used = sum((l.debit-l.credit for l in lines if l.account.code=='1032' and l.entry.kind=='advance-use'),ZERO)
        products_by_code = defaultdict(lambda: ZERO)
        products_by_code['702'] = funding-fund_used-advance_used
        products_by_code['705'] = fund_used
        products_by_code['703'] = advance_used
        for line in lines:
            if line.account.code.startswith('7') and line.entry.kind!='project-complete':
                products_by_code[line.account.code] += line.credit-line.debit
        assigned_products = sum((v for code,v in products_by_code.items() if code not in ('702','703','705','706')),ZERO)
        row = {'id':p.pk,'project':p.name,'key':p.key.name,'decision':p.decision,
               'voted_on':str(p.decided_on or ''),'voted':m(p.budget),'expenses':m(costs),
               'paid':m(sum((pay.amount for pay in ExpensePayment.objects.filter(expense__project=p,entry__date__lte=year.ends_on)
                    .exclude(entry__reversal__date__lte=year.ends_on)),ZERO)+sum((l.credit-l.debit for l in cash if not hasattr(l.entry,'expense_payment') and not (l.entry.reversal_of_id and hasattr(l.entry.reversal_of,'expense_payment'))),ZERO)),
               'funding':m(funding),'subsidies':m(amount(received,-1)),
               'assigned_products':m(assigned_products),'net_expenses':m(costs-assigned_products),
               'balance':m(funding+assigned_products-costs),
               'expense_details':{k:m(v) for k,v in expenses_by_code.items()},
               'product_details':{k:m(v) for k,v in products_by_code.items()},
               'receivable':m(amount(receivable)), 'waiting':m(funding+amount(received,-1)+assigned_products-costs),
               'completed_on':str(p.completed_on or ''),
               'details': [{'date':str(l.entry.date),'number':l.entry.number,'label':l.entry.label,
                            'code':l.account.code,'debit':m(l.debit),'credit':m(l.credit)} for l in lines]}
        if p.completed_on and year.starts_on <= p.completed_on <= year.ends_on:
            completed.append(row)
        elif (not p.completed_on or p.completed_on>year.ends_on) and (lines or p.decided_on):
            pending.append(row)
    return completed,pending


def financial_state(year, reg, pending):
    balances = defaultdict(lambda:ZERO)
    labels, names = {}, {}
    query = Line.objects.filter(entry__year=year).exclude(entry__kind='closing').select_related('account','owner','supplier','entry')
    for line in query:
        code = line.account.code
        if code.startswith(('6','7')):
            continue
        identity = (code, line.owner_id, line.supplier_id)
        balances[identity] += line.debit-line.credit
        labels[identity] = line.account.name
        names[identity] = str(line.owner) if line.owner_id else line.supplier.name if line.supplier_id else ''
    simulated = not AnnualSettlement.objects.filter(year=year,active=True).exists()
    if simulated:
        for row in reg['rows']:
            identity = ('450',row['owner'],None)
            balances[identity] += Decimal(row['adjustment'])
            labels[identity] = 'Copropriétaires après répartition proposée'
            names[identity] = row.get('owner_name',row.get('name',str(row['owner'])))
    pending_ids = [r['id'] for r in pending]
    # Legacy journals retain 102 financing and 120 prior costs separately. Regroup
    # these in the pending-operation balance (12) for the annual presentation.
    for line in query.filter(project_id__in=pending_ids).filter(Q(account__code__in=['102','120']) | Q(account__code__startswith='13')):
        balances[(line.account.code,line.owner_id,line.supplier_id)] -= line.debit-line.credit
    # Calculate the presentation balance independently from the year's ledger,
    # including carried balances, rather than copying annex 5's lifetime total.
    waiting = ZERO
    for line in query.filter(project_id__in=pending_ids):
        if line.account.code in ('102','120') or line.account.code.startswith(('13','7')):
            waiting += line.credit-line.debit
        elif line.account.code.startswith('67'):
            waiting -= line.debit-line.credit
    if waiting:
        balances[('12',None,None)] -= waiting
        labels[('12',None,None)] = 'Solde en attente sur travaux (annexe 5)'
        names[('12',None,None)] = ''
    result = []
    for identity,value in sorted(balances.items(),key=lambda x:(x[0][0],x[0][1] or 0,x[0][2] or 0)):
        if not value: continue
        code,owner,supplier = identity
        category = 'Trésorerie' if code.startswith('5') else 'Avances, provisions et fonds' if code.startswith('1') else 'Créances et dettes'
        # Distinct tiers with identical names are kept distinct before summing.
        result.append({'identity':f'{code}:{owner or 0}:{supplier or 0}','code':code,'label':labels[identity],
            'third_party':names[identity],'group':category,'debit':m(max(value,ZERO)),
            'credit':m(max(-value,ZERO))})
    return result,simulated


def build(year, reg):
    from .cycle import regularization_data, digest
    previous = FiscalYear.objects.filter(ends_on__lt=year.starts_on).order_by('-ends_on').first()
    following = list(FiscalYear.objects.filter(starts_on__gt=year.ends_on).order_by('starts_on')[:2])
    completed,pending = project_states(year)
    state,simulated = financial_state(year,reg,pending)
    before = []
    if previous:
        saved = getattr(previous,'closure',None) if hasattr(previous,'closure') else None
        # Older closures are deliberately not regenerated as a new certified pack.
        if saved and saved.snapshot.get('regulatory'):
            before = saved.snapshot['regulatory']['annexes'][0]['rows']
        else:
            _,old_pending = project_states(previous)
            old_reg = AnnualSettlement.objects.filter(year=previous,active=True).first()
            before,_ = financial_state(previous,old_reg.data if old_reg else regularization_data(previous),old_pending)
    old = {r['identity']:r for r in before}
    now = {r['identity']:r for r in state}
    state = [{**(now.get(key) or old[key]),'debit':now.get(key,{}).get('debit','0.00'),
              'credit':now.get(key,{}).get('credit','0.00'),
              'previous_debit':old.get(key,{}).get('debit','0.00') if previous else None,
              'previous_credit':old.get(key,{}).get('credit','0.00') if previous else None} for key in sorted(set(old)|set(now))]
    def current(selected):
        result = defaultdict(lambda:ZERO)
        if selected:
            for l in Line.objects.filter(entry__year=selected).exclude(entry__kind__in=['closing','regularization']).select_related('account'):
                if not l.project_id and l.account.code.startswith(('6','7')) and not l.account.code.startswith('67') and l.account.code not in WORK_PRODUCTS:
                    result[(l.account.code,l.key_id)] += (l.debit-l.credit)*(1 if l.account.code.startswith('6') else -1)
        return result
    def budgets(selected):
        specific,centres = {},defaultdict(lambda:ZERO)
        if selected:
            for b in Budget.objects.filter(year=selected).select_related('account'):
                key = (b.account.code,b.key_id)
                if b.cost_center_id is None: specific[key] = b.amount
                else: centres[key] += b.amount
        return {key:specific.get(key,centres.get(key)) for key in set(specific)|set(centres)}
    from .models import Account, ChargeKey
    from .services import CHART
    names = {**CHART,**dict(Account.objects.values_list('code','name'))}
    keys = dict(ChargeKey.objects.values_list('id','name'))
    actual, prior, planned = current(year),current(previous),budgets(year)
    future = [budgets(following[i] if len(following)>i else None) for i in range(2)]
    rows = []
    for identity in sorted(set(actual)|set(prior)|set(planned)|set(future[0])|set(future[1]),key=lambda x:(x[1] or 0,x[0])):
        code,key = identity
        rows.append({'code':code,'label':names.get(code,code),'key':keys.get(key,'Non ventilé'),
            'side':'Charges' if code.startswith('6') else 'Produits',
            'actual_previous':m(prior.get(identity,ZERO)) if previous else None,
            'budget_current':m(planned[identity]) if identity in planned else None,
            'actual_current':m(actual.get(identity,ZERO)),
            'budget_next':m(future[0][identity]) if identity in future[0] else None,
            'budget_following':m(future[1][identity]) if identity in future[1] else None})
    general = {}
    for r in rows:
        if r['code'] not in general:
            general[r['code']] = {**r,'key':'Toutes clés',**{k:None for k in ['actual_previous','budget_current','actual_current','budget_next','budget_following']}}
        g = general[r['code']]
        for k in ['actual_previous','budget_current','actual_current','budget_next','budget_following']:
            if r[k] is not None: g[k] = m(Decimal(g[k] or '0')+Decimal(r[k]))
    expenses = sum((Decimal(r['expenses']) for r in completed),ZERO)
    annex2 = [dict(r,activity='Opérations courantes') for r in general.values()]
    previous_completed = project_states(previous)[0] if previous else []
    exceptional, old_exceptional = defaultdict(lambda:ZERO),defaultdict(lambda:ZERO)
    for projects, target in [(completed,exceptional),(previous_completed,old_exceptional)]:
        for project in projects:
            for field in ['expense_details','product_details']:
                for code,value in project[field].items(): target[code] += Decimal(value)
    for code in sorted(set(exceptional)|set(old_exceptional)|{'671','702','703','705'}):
        annex2.append({'code':code,'label':names.get(code,code),'side':'Charges' if code.startswith('6') else 'Produits',
            'activity':'Travaux terminés','actual_current':m(exceptional[code]),
            'actual_previous':m(old_exceptional[code]) if previous else None,'budget_current':None,'budget_next':None,'budget_following':None})
    errors = list(reg.get('errors',[]))
    warnings = []
    totals = {k:sum((Decimal(r[k]) for r in state),ZERO) for k in ['debit','credit']}
    delta = totals['debit']-totals['credit']
    checks = [{'label':'Annexe 1 : équilibre après répartition','left':m(totals['debit']),'right':m(totals['credit']),'ok':delta==0},
              {'label':'Annexes 2 et 4 : charges des opérations terminées','left':m(sum((Decimal(r['actual_current']) for r in annex2 if r['activity']=='Travaux terminés' and r['side']=='Charges'),ZERO)),
               'right':m(sum((Decimal(r['expenses']) for r in completed),ZERO)),'ok':True},
              {'label':'Annexes 1 et 5 : solde en attente des travaux','left':m(sum((Decimal(r['credit'])-Decimal(r['debit']) for r in state if r['code']=='12'),ZERO)),
               'right':m(sum((Decimal(r['waiting']) for r in pending),ZERO)),'ok':True}]
    ledger_works = Line.objects.filter(entry__year=year,account__code__startswith='67').exclude(entry__kind='closing')
    pending_ids = [r['id'] for r in pending]
    recognized = sum((l.debit-l.credit for l in ledger_works.exclude(project_id__in=pending_ids)),ZERO)
    checks.append({'label':'Annexe 4 et grand livre : travaux terminés ou non attribués','left':m(expenses),'right':m(recognized),'ok':expenses==recognized})
    current_totals = {side:sum((Decimal(r['actual_current']) for r in rows if r['side']==side),ZERO) for side in ['Charges','Produits']}
    for side in ['Charges','Produits']:
        check = sum((Decimal(r['actual_current']) for r in annex2 if r['activity']=='Opérations courantes' and r['side']==side),ZERO)
        checks.append({'label':f'Annexes 2 et 3 : {side.lower()} courants','left':m(check),'right':m(current_totals[side]),'ok':check==current_totals[side]})
    for c in checks:
        c['ok'] = c['left']==c['right']
        if not c['ok']: errors.append(c['label']+' : écart à expliquer.')
    if simulated: warnings.append('État financier après répartition proposée : la régularisation n’est pas comptabilisée. Faire approuver les comptes avant de l’appliquer.')
    if not previous: warnings.append('Aucun exercice précédent : comparatif N−1 non disponible, les cases restent vides.')
    if len(following)<2: warnings.append('Créer les exercices et saisir les budgets futurs pour compléter les colonnes N+1 et N+2.')
    if any(r['key']=='Non ventilé' and Decimal(r['actual_current']) for r in rows): errors.append('Des opérations courantes ne sont pas ventilées par clé.')
    for p in completed+pending:
        if not p['voted_on']: errors.append('Travaux « '+p['project']+' » : date de la décision manquante.')
    if Line.objects.filter(entry__year=year,account__code__in=['1031','1032','1033']).filter(Q(lot__isnull=True)|Q(owner__isnull=True)).exists():
        errors.append('Des avances ne sont pas ventilées par lot et titulaire.')
    if previous and not previous.closed and Line.objects.filter(entry__year=previous).exists():
        warnings.append('L’exercice précédent n’est pas clôturé : vérifier son approbation et ses reports avant utilisation officielle du comparatif.')
    if any(Decimal(r['waiting']) < 0 for r in pending):
        warnings.append('Des travaux présentent un solde en attente débiteur : il reste des dépenses à financer ; conserver le signe négatif.')
    if any(Decimal(r['paid']) > Decimal(r['expenses']) for r in completed+pending):
        errors.append('Des règlements de travaux dépassent les dépenses enregistrées : vérifier les acomptes et avoirs avant validation.')
    if Line.objects.filter(entry__year=year,account__code__in=WORK_PRODUCTS,project__isnull=True).exclude(entry__kind='closing').exists():
        errors.append('Des produits exceptionnels ne sont pas rattachés à leur opération de travaux.')
    if Line.objects.filter(entry__year=year,account__code__in=['106','674','706']).exclude(entry__kind='closing').exists():
        errors.append('Délégation de pouvoirs au conseil : vérifier l’opération, ses engagements et son compte rendu dans un état complémentaire.')
    if Line.objects.filter(entry__year=year).filter(Q(account__code__startswith='66')|Q(account__code__startswith='68')).exists():
        errors.append('Charges financières ou dépréciations : vérifier leur ventilation et les états spécifiques avant validation de ce modèle.')
    budget_groups = defaultdict(set)
    for item in Budget.objects.filter(year=year): budget_groups[item.account_id].add(item.key_id)
    if any(None in keys and len(keys)>1 for keys in budget_groups.values()):
        errors.append('Un même compte possède un budget global et des budgets par clé : préciser le niveau retenu avant validation, sans double comptage.')
    if Line.objects.filter(entry__year=year,account__code__startswith='16').exists():
        errors.append('Emprunt collectif présent : compléter et faire valider son échéancier et ses états spécifiques avant utilisation de ce modèle en AG.')
    unsupported=[r['code'] for r in state if not r['code'].startswith(('102','1031','1032','1033','105','106','12','131','16','40','42','43','44','45','46','47','48','49','50','51','53'))]
    if unsupported:errors.append('Comptes sans rubrique dans ce modèle annuel : '+', '.join(sorted(set(unsupported)))+'. Préparer leur état complémentaire avant validation.')
    if Line.objects.filter(entry__year=year,account__code__startswith='13',project__isnull=True).exists():
        errors.append('Subvention sans opération identifiée : rapprocher la notification et son échéancier d’imputation avant validation.')
    if Line.objects.filter(entry__date__lte=year.ends_on,project_id__in=[r['id'] for r in completed+pending]).filter(Q(account__code__startswith='13')|Q(account__code__in=['711','712','713'])).exists():
        errors.append('Une opération comporte une aide, un emprunt ou une indemnité : rapprocher ses engagements, versements et imputations dans un état complémentaire avant utilisation en AG.')
    org,_ = Organization.objects.get_or_create(pk=1)
    pack = {'version':MODEL_VERSION,'organization':org.name,'address':org.address,'year':year.name,
        'period':{'start':str(year.starts_on),'end':str(year.ends_on)},
        'comparison':{'previous':previous.name if previous else None,'next':following[0].name if following else None,'following':following[1].name if len(following)>1 else None},
        'after_allocation':'proposed' if simulated else 'posted','checks':checks,'errors':list(dict.fromkeys(errors)),'warnings':warnings,
        'notes':['Soldes débiteurs et créditeurs séparés par tiers identifié, sans compensation entre personnes distinctes.',
                 'La présentation du compte 12 regroupe les financements 102 et coûts en attente 120 des opérations non terminées, avec leurs charges de l’exercice. Elle ne modifie aucune écriture.',
                 'Une case vide désigne une donnée non renseignée, pas un montant nul. Les engagements non comptabilisés et prêts collectifs nécessitent leurs pièces complémentaires.'],
        'sources':[{'title':'Décret n° 2005-240 — comptes et annexes','url':SOURCE}],
        'annexes':[
            {'number':1,'title':'État financier après répartition','columns':['group','code','label','third_party','previous_debit','previous_credit','debit','credit'],'rows':state},
            {'number':2,'title':'Compte de gestion général','columns':['activity','side','code','label','actual_previous','budget_current','actual_current','budget_next','budget_following'],'rows':annex2},
            {'number':3,'title':'Opérations courantes par clé de répartition','columns':['key','side','code','label','actual_previous','budget_current','actual_current','budget_next','budget_following'],'rows':rows},
            {'number':4,'title':'Travaux et opérations exceptionnelles terminés','columns':['project','key','voted_on','voted','expenses','assigned_products','net_expenses','funding','balance','completed_on'],'rows':completed},
            {'number':5,'title':'Travaux et opérations exceptionnelles non terminés','columns':['project','key','voted_on','voted','paid','expenses','funding','subsidies','waiting','receivable'],'rows':pending}]}
    pack['source_ledger_hash'] = digest(list(Line.objects.filter(entry__year=year).exclude(entry__kind='closing').order_by('id')
        .values('id','entry_id','entry__date','entry__journal','entry__label','entry__reference','account__code',
                'owner_id','supplier_id','lot_id','key_id','project_id','debit','credit')))
    pack['source_hash'] = digest(pack)
    return pack
