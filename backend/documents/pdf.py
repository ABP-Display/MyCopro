"""Private, server-side editions of reviewed sources (never a certification).

All text is escaped. Tables repeat their headers and split long cells rather than
truncate resolutions, names or monetary values. No browser assets are fetched.
"""
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from .legal import CORRESPONDENCE_REMINDERS
from django.utils import timezone
from django.utils.dateparse import parse_datetime

FONT_DIR=Path(reportlab.__file__).parent/'fonts'
pdfmetrics.registerFont(TTFont('Copro',str(FONT_DIR/'Vera.ttf')))
pdfmetrics.registerFont(TTFont('Copro-Bold',str(FONT_DIR/'VeraBd.ttf')))
pdfmetrics.registerFontFamily('Copro',normal='Copro',bold='Copro-Bold',italic='Copro',boldItalic='Copro-Bold')
INK=colors.HexColor('#163b35')
PALE=colors.HexColor('#edf5f2')
STYLES=getSampleStyleSheet()
for name in ['Normal','Heading1','Heading2','Heading3']:
    STYLES[name].fontName='Copro-Bold' if name!='Normal' else 'Copro'
    STYLES[name].textColor=INK
STYLES['Normal'].fontSize=9;STYLES['Normal'].leading=13
CELL=ParagraphStyle('Cell',parent=STYLES['Normal'],fontSize=7,leading=9,wordWrap='CJK')
NUMBER=ParagraphStyle('Number',parent=CELL,alignment=TA_RIGHT)


def p(value,style='Normal'):
    return Paragraph(escape(str(value if value is not None else '—')).replace('\n','<br/>'),STYLES[style])


def money(value):
    if value is None:return '—'
    return f'{Decimal(str(value)):,.2f}'.replace(',',' ').replace('.',',')


def meeting_time(value):
    return timezone.localtime(parse_datetime(value)).strftime('%d/%m/%Y à %H:%M')


def table(headers,rows,widths,numeric=()):
    def cell(value,i):return Paragraph(escape(str(value if value is not None else '—')).replace('\n','<br/>'),NUMBER if i in numeric else CELL)
    data=[[cell(v,i) for i,v in enumerate(headers)]]
    data += [[cell(v,i) for i,v in enumerate(row)] for row in rows]
    if len(data)==1:data.append([cell('Néant' if i==0 else '',i) for i in range(len(headers))])
    obj=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT',splitByRow=1,splitInRow=1)
    obj.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('GRID',(0,0),(-1,-1),.3,colors.HexColor('#c8d8d2')),
        ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    return obj


def annual(story,src,width):
    pack=src['annexes']; years=pack['comparison']
    story.extend([p('Dossier annuel — cinq annexes et décomptes','Heading1'),p(pack['year']+' · '+pack['period']['start']+' au '+pack['period']['end']),
        p('Montants en euros. Répartition '+('comptabilisée' if pack['after_allocation']=='posted' else 'proposée : approbation des comptes requise avant comptabilisation.'))])
    for label,items in [('Points à corriger',pack['errors']),('Points de vigilance',pack['warnings'])]:
        if items:story.append(p(label,'Heading2'))
        story.extend(p('• '+x) for x in items)
    story.append(p('Contrôles de concordance','Heading2'))
    story.append(table(['Contrôle','Gauche','Droite','Résultat'],[[r['label'],money(r['left']),money(r['right']),'Concordant' if r['ok'] else 'Écart'] for r in pack['checks']],[width*.6,width*.13,width*.13,width*.14],(1,2)))
    for annex in pack['annexes']:
        number=annex['number']; rows=annex['rows']
        story.extend([PageBreak(),p(f'Annexe {number} — '+annex['title'],'Heading1'),p('N−1 : '+str(years['previous'] or 'non disponible')+' · N : '+pack['year']+' · N+1 : '+str(years['next'] or 'non renseigné')+' · N+2 : '+str(years['following'] or 'non renseigné'))])
        if number==1:
            grand=[Decimal('0'),Decimal('0')]
            for section,title in [(1,'I. Situation financière et trésorerie'),(2,'II. Créances et dettes')]:
                story.append(p(title,'Heading2'))
                assets=[];liabilities=[]
                # Keep every prescribed heading, even when its recorded balance is zero.
                schemas=(
                    [[('50','Fonds placés'),('51','Banques et disponibilités'),('53','Caisse')],
                     [('102','Provisions travaux'),('1031','Avances de trésorerie'),('1032','Avances PPT'),('1033','Autres avances'),('105','Fonds travaux'),('106','Provisions délégation conseil'),('131','Subventions en instance d’affectation'),('12','Solde en attente travaux')]] if section==1 else
                    [[('45','Copropriétaires — sommes exigibles'),('459','Copropriétaires douteux'),('40','Fournisseurs débiteurs'),('42/44','Autres créances'),('46','Débiteurs divers'),('47','Comptes d’attente'),('48','Comptes de régularisation')],
                     [('45','Copropriétaires créditeurs'),('40','Fournisseurs créditeurs'),('42/44','Autres dettes'),('46','Créditeurs divers'),('47','Comptes d’attente'),('48','Comptes de régularisation'),('49','Dépréciations des comptes de tiers')]])
                for side,schema in enumerate(schemas):
                    for prefix,label in schema:
                        selected=[r for r in rows if (r['code'].startswith(('42','43','44')) if prefix=='42/44' else r['code'].startswith(prefix)) and not (side==0 and prefix=='45' and r['code'].startswith('459'))]
                        def value(previous=False):
                            if previous and not years['previous']:return None
                            def amount(r,field):return Decimal(r[('previous_' if previous else '')+field] or '0')
                            if section==1:return sum((amount(r,'debit' if side==0 else 'credit')-amount(r,'credit' if side==0 else 'debit') for r in selected),Decimal('0'))
                            return sum((amount(r,'debit' if side==0 else 'credit') for r in selected),Decimal('0'))
                        (assets if side==0 else liabilities).append((prefix+' '+label,value(True),value()))
                result=[]
                for i in range(max(len(assets),len(liabilities))):
                    a=assets[i] if i<len(assets) else ('',None,None);b=liabilities[i] if i<len(liabilities) else ('',None,None)
                    result.append([a[0],money(a[1]),money(a[2]),b[0],money(b[1]),money(b[2])])
                def sums(items,col):return sum((Decimal(r[col] or '0') for r in items),Decimal('0')) if col!=1 or years['previous'] else None
                result.append(['Total '+str(section),money(sums(assets,1)),money(sums(assets,2)),'Total '+str(section),money(sums(liabilities,1)),money(sums(liabilities,2))])
                grand[0]+=sums(assets,2);grand[1]+=sums(liabilities,2)
                story.append(table(['Trésorerie / créances','N−1','N','Provisions / dettes','N−1','N'],result,[width*.29,width*.10,width*.11,width*.29,width*.10,width*.11],(1,2,4,5)))
            story.append(p('Total général I + II : trésorerie et créances '+money(grand[0])+' € ; provisions et dettes '+money(grand[1])+' €. Les banques créditrices sont présentées avec leur signe négatif en trésorerie.'))
            story.append(p('Emprunts collectifs restant dus : état spécifique requis si un compte 16 est utilisé. Aucune absence d’échéancier ne vaut solde nul.'))
            story.append(p('Détail nominatif des soldes de tiers','Heading3'))
            story.append(table(['Compte','Tiers','N−1 débiteur','N−1 créditeur','N débiteur','N créditeur'],[[r['code'],r['third_party'],money(r['previous_debit']),money(r['previous_credit']),money(r['debit']),money(r['credit'])] for r in rows if r['third_party']],[width*.07,width*.41]+[width*.13]*4,(2,3,4,5)))
        elif number==2:
            cols=['actual_previous','budget_current','actual_current','budget_next','budget_following']
            for activity in ['Opérations courantes','Travaux terminés']:
                story.append(p(activity,'Heading2'))
                sides=[[r for r in rows if r['activity']==activity and r['side']==side] for side in ['Charges','Produits']]
                data=[]
                for i in range(max(len(sides[0]),len(sides[1]))):
                    pair=[]
                    for side in sides:
                        r=side[i] if i<len(side) else None
                        pair+=([r['code']+' '+r['label']]+[money(r[k]) for k in cols]) if r else ['']*6
                    data.append(pair)
                totals=[[sum((Decimal(r[k] or '0') for r in side),Decimal('0')) if any(r[k] is not None for r in side) else None for k in cols] for side in sides]
                data.append(['Sous-total charges']+[money(v) for v in totals[0]]+['Sous-total produits']+[money(v) for v in totals[1]])
                story.append(table(['Charges','Réalisé N−1','Budget N','Réalisé N','Budget N+1','Budget N+2','Produits','Réalisé N−1','Budget N','Réalisé N','Budget N+1','Budget N+2'],data,[width*.18]+[width*.064]*5+[width*.18]+[width*.064]*5,tuple(i for i in range(12) if i not in (0,6))))
                difference=(totals[1][2] or 0)-(totals[0][2] or 0)
                story.append(p('Solde avant répartition N (produits − charges) : '+money(difference)+' €. '+('Excédent' if difference>=0 else 'Insuffisance')+' à rapprocher des décomptes.'))
        elif number==3:
            for key in dict.fromkeys(r['key'] for r in rows):
                story.append(p(key,'Heading2')); group=[r for r in rows if r['key']==key]
                cols=['actual_previous','budget_current','actual_current','budget_next','budget_following']
                data=[[r['side']+' · '+r['code']+' '+r['label']]+[money(r[k]) for k in cols] for r in group]
                data.append(['Net charges − produits']+[money(sum((Decimal(r[k] or '0')*(1 if r['side']=='Charges' else -1) for r in group),Decimal('0'))) if any(r[k] is not None for r in group) else '—' for k in cols])
                story.append(table(['Compte / sens','Réalisé N−1','Budget N','Réalisé N','Budget N+1','Budget N+2'],data,[width*.40]+[width*.12]*5,(1,2,3,4,5)))
            if not rows:story.append(p('Néant : aucune opération courante enregistrée.'))
        else:
            fields=['project','key','voted_on','voted','expenses','assigned_products','net_expenses','funding','balance','completed_on'] if number==4 else ['project','key','voted_on','voted','paid','expenses','funding','subsidies','waiting','receivable']
            labels=['Opération','Clé','Vote','Budget voté','Charges','Produits affectés','Net charges','Provisions / affectations','Solde avant répartition','Terminée le'] if number==4 else ['Opération','Clé','Vote','A. Votés','B. Payés','C. Réalisés','D. Appels / affectations','Aides inscrites','E. Solde attente','F. À recevoir']
            numeric=range(3,9) if number==4 else range(3,10)
            data=[[money(r[k]) if i in numeric else r[k] for i,k in enumerate(fields)] for r in rows]
            story.append(table(labels,data,[width*.18,width*.10,width*.10]+[width*(.62/7)]*7,numeric))
            if number==5:story.append(p('E = D + aides inscrites + autres produits affectés − C. Le détail des dates de paiement, réalisation et financement figure ci-dessous. Les prêts et aides complexes bloquent l’édition validée.'))
            for row in rows:
                story.extend([p(row['project']+' — '+row['decision'],'Heading2'),p('Financement : '+', '.join(code+' : '+money(v)+' €' for code,v in row['product_details'].items()))])
                story.append(table(['Date','N°','Compte','Écriture source','Débit','Crédit'],[[r['date'],r['number'],r['code'],r['label'],money(r['debit']),money(r['credit'])] for r in row['details']],[width*.10,width*.07,width*.07,width*.50,width*.13,width*.13],(4,5)))
    story.extend([PageBreak(),p('Décomptes individuels — annexe au dossier','Heading1')])
    allocations=src['individual_allocations']
    story.append(table(['Titulaire / lot','Charges','Provisions','Régularisation'],[[str(r.get('owner_name',r.get('name',r.get('owner',''))))+' / '+str(r.get('lot_number',r.get('lot',''))),money(r.get('actual',0)),money(r.get('provisions',0)),money(r.get('adjustment',0))] for r in allocations],[width*.49,width*.17,width*.17,width*.17],(1,2,3)))
    for note in pack['notes']:story.append(p(note))


def assembly(story,src,document,width):
    packet=src['packet']; minutes=src.get('minutes',{})
    titles={'invitation':'Convocation à l’assemblée générale','correspondence':'Formulaire de vote par correspondance','power':'Pouvoir de représentation','attendance':'Feuille de présence','minutes':'Procès-verbal de l’assemblée générale'}
    story.extend([p(titles[document],'Heading1'),p(packet['title'],'Heading2'),p('Immeuble(s) : '+packet.get('building_address','À compléter')),
        p('Assemblée : '+meeting_time(packet['scheduled_at'])+' · '+packet['location']),p('Organisateur : '+packet.get('organizer',''))])
    if document=='invitation':
        story.extend([p('Madame, Monsieur, vous êtes convoqué(e) à l’assemblée ci-dessus. Sont joints le présent ordre du jour, les pièces désignées pour chaque résolution, le formulaire de vote par correspondance et le pouvoir.'),p('Consultation des justificatifs','Heading2'),p(packet['consultation'])])
        for r in packet['resolutions']:
            story.extend([p(str(r['position'])+'. '+r['title'],'Heading2'),p('Majorité proposée : article '+r['majority']),p(r['text'])])
            for piece in r['pieces']:story.append(p('Pièce jointe : '+piece['label']+' — '+piece['title']+' ('+piece['filename']+', version '+str(piece['id'])+')'))
        story.append(p('Retour du vote par correspondance au plus tard le '+packet['correspondence_deadline']+' · '+packet['return_address']+' · '+packet.get('return_email','À compléter')))
    elif document=='correspondence':
        story.extend([p('Formulaire à adresser à : '+packet['organizer']),p('Adresse postale : '+packet['return_address']),p('Adresse électronique : '+packet.get('return_email','À compléter')),
            p('À réceptionner au plus tard le '+packet['correspondence_deadline']),
            p('Je soussigné(e) (nom et domicile) :\n................................................................................................\n................................................................................................'),
            p('Agissant en qualité de : [ ] copropriétaire  [ ] associé\n[ ] mandataire commun des copropriétaires en indivision ou en démembrement du droit de propriété'),
            p('Après avoir pris connaissance de l’ordre du jour et des documents annexés à la convocation ou mis à disposition sur le site en ligne sécurisé de la copropriété, souhaite émettre sur chacune des questions soumises à la délibération de l’assemblée générale convoquée aux date, heure et lieu indiqués ci-dessus le vote exprimé dans le tableau joint.'),
            p('Nombre de pages du tableau de vote jointes : ........ (à compléter).'),p('Fait à ................................, le ........................\nSignature :\n\n')])
        for r in packet['resolutions']:
            story.extend([PageBreak(),p('Tableau de vote — question '+str(r['position']),'Heading1'),
                p('Nom du copropriétaire / associé / mandataire commun : ....................................................'),
                p('Immeuble(s) : '+packet.get('building_address','À compléter')+'\nDate de l’assemblée : '+meeting_time(packet['scheduled_at']))])
            story.append(table(['Identification de l’objet','Questions suivant l’ordre du jour','POUR','CONTRE','ABSTENTION'],[[r['title'],str(r['position'])+'. '+r['title']+'\n'+r['text'],'[ ]','[ ]','[ ]']],[width*.22,width*.48,width*.09,width*.10,width*.11]))
            story.extend([Spacer(1,18),p('Cocher une seule case par question. Parapher chaque page intermédiaire et signer la dernière page du tableau.\nSignature / paraphe :')])
        story.extend([PageBreak(),p('Rappel des dispositions légales et réglementaires','Heading1')])
        for title,text in CORRESPONDENCE_REMINDERS:story.extend([p(title,'Heading3'),p(text)])
    elif document=='power':
        story.extend([p('Je soussigné(e) (nom, domicile, lots) :\n................................................................................................\n................................................................................................'),
            p('Donne mandat à (nom et domicile) :\n................................................................................................\n................................................................................................'),
            p('Pour me représenter à l’assemblée indiquée ci-dessus et voter les résolutions inscrites à son ordre du jour. Consignes éventuelles :\n................................................................................................\n................................................................................................'),
            p('Le mandat et le mandataire doivent respecter les interdictions et limites de l’article 22 de la loi du 10 juillet 1965, à contrôler à l’enregistrement du pouvoir.'),p('Fait à ................................, le ........................\nSignature du mandant :')])
    elif document=='attendance':
        participants=src.get('participants',[])
        data=[]
        for elector in packet['electors']:
            part=next((r for r in participants if r['elector']==elector['elector']),{})
            attendance={'absent':'Absent','present':'Présent','represented':'Représenté','correspondence':'Vote par correspondance'}.get(part.get('attendance','absent'),'À préciser')
            data.append([elector['name']+'\n'+elector['address'],', '.join(map(str,elector['lots'])),elector['shares'],attendance+'\n'+part.get('representative','')+' '+part.get('representative_address','')+'\nFormulaire reçu : '+str(part.get('received_on','—')),''])
        story.extend([table(['Nom et domicile','Lots','Voix','Participation / représentant','Émargement'],data,[width*.32,width*.10,width*.10,width*.31,width*.17],(2,)),p('Certifiée exacte par le président de séance :\nNom, date et signature :')])
    else:
        bureau=minutes.get('bureau',{})
        story.append(p('Président : '+bureau.get('president','À préciser')+'\nSecrétaire : '+bureau.get('secretary','À préciser')+'\nScrutateur(s) : '+(bureau.get('scrutineers') or 'Aucun')))
        for item in minutes.get('resolutions',[]):
            r=item['resolution']; votes=item['votes']
            story.extend([p(str(r['position'])+'. '+r['title'],'Heading2'),p(votes[-1]['amendment'] or r['text']),p('Décision : '+('ADOPTÉE' if item['adopted'] else 'NON ADOPTÉE'))])
            for v in votes:
                result=v['result']
                story.extend([p('Tour '+str(v['tour'])+' · article '+result['rule']+' · pour : '+str(result['for_votes'])+' ; contre : '+str(result['against_votes'])+' ; abstention : '+str(result['abstain_votes'])),p(result['explanation']),p('Incidents / réserves : '+(v.get('incident') or 'Aucun'))])
            for group,label in [('against','Contre'),('for','Pour'),('abstain','Abstentions'),('absent','Défaillants'),('deemed_default','Assimilés défaillants — vote favorable par correspondance sur un texte amendé')]:
                story.append(p(label+' : '+('; '.join(x['name']+' ('+str(x['shares'])+' voix)' for x in item['groups'].get(group,[])) or 'Aucun')))
        story.extend([p('Observations : '+minutes.get('remarks','')),p(minutes.get('appeal_notice','')),p('Président, secrétaire et scrutateurs : noms, dates et signatures\n\n\n'),p('Annexe : feuille de présence certifiée, formulaires et pouvoirs à conserver avec le PV. Les signatures et la notification restent à réaliser et à enregistrer dans le parcours AG.')])


def render(current,document,decision=None):
    src=current['payload']; kind=src['kind']
    allowed={'accounting':['annexes'],'assembly':['invitation','correspondence','power'],'minutes':['minutes','attendance']}
    if document not in allowed[kind]:raise ValueError('Document non disponible pour ce dossier.')
    stream=BytesIO(); page=landscape(A4) if kind=='accounting' or document=='attendance' else A4
    doc=SimpleDocTemplate(stream,pagesize=page,rightMargin=30,leftMargin=30,topMargin=74,bottomMargin=62,title='Copro. — '+current['title'],author='Copro.')
    width=page[0]-60; story=[p(src['organization']['name'],'Heading2'),p(src['organization']['address'])]
    running=None
    if document=='correspondence':
        packet=src['packet']
        running=p('Immeuble(s) : '+packet.get('building_address','À compléter')+'\nNom / qualité du votant : ..................................................................\nDate de l’AG : '+meeting_time(packet['scheduled_at']))
        _,height=running.wrap(width,1000)
        doc.topMargin=68+height+14
    stamp=('RELECTURE MÉTIER ENREGISTRÉE — '+decision.reviewer+' · '+str(decision.reviewed_on)) if decision else 'PROJET — VALIDATION MÉTIER REQUISE'
    def frame(canvas,document_obj):
        canvas.saveState();canvas.setFont('Copro-Bold',9);canvas.setFillColor(INK)
        canvas.drawString(30,page[1]-28,'Copro. · '+src['organization']['name'][:100]);canvas.setFont('Copro',7)
        canvas.drawString(30,page[1]-42,stamp[:150]);canvas.drawString(30,page[1]-54,src['organization']['address'].replace('\n',', ')[:155])
        if running:running.drawOn(canvas,30,page[1]-66-height)
        canvas.drawString(30,34,'Version '+src['model_version']+' · source '+current['source_hash'][:24]+' · page '+str(document_obj.page))
        canvas.drawString(30,23,'Relecture déclarée, sans certification automatique. Les signatures et envois restent à effectuer.' if decision else 'Document de travail. Corriger les alertes et faire relire avant toute utilisation officielle.')
        canvas.restoreState()
    if kind=='accounting':annual(story,src,width)
    else:assembly(story,src,document,width)
    story.extend([Spacer(1,15),p('Référence du dossier : '+current['source_hash']),p('Modèle : '+src['model_version'])])
    if decision:story.extend([p('Relecture enregistrée par '+decision.reviewer+' ('+decision.qualification+') le '+str(decision.reviewed_on)),p('Conclusion : '+decision.observations),p('Rapport joint : version '+str(decision.proof_id)+' · empreinte '+decision.proof_checksum)])
    doc.build(story,onFirstPage=frame,onLaterPages=frame)
    return stream.getvalue()
