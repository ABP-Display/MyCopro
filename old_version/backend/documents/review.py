"""Review control for generated documents. A recorded declaration is not certification."""
from datetime import date
import hashlib
from pathlib import Path
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils import timezone
import json
from finance.cycle import annexes, digest
from finance.models import FiscalYear, YearClosure, Organization
from finance.regulatory import MODEL_VERSION
from governance.models import AssemblyWorkflow
from .models import DossierReview, Version

EXPORT_VERSION = 'documents-2026.10.2'
_ROOT=Path(__file__).resolve().parent.parent
TEMPLATE_HASH=hashlib.sha256(b''.join((_ROOT/name).read_bytes() for name in
    ['documents/pdf.py','documents/legal.py','documents/review.py','finance/regulatory.py','governance/templates.py'])).hexdigest()
CHECKLISTS = {
    'accounting': {
        'identity':'Identité du syndicat, adresse et exercice contrôlés',
        'reconciliation':'Balance, banque, tiers et justificatifs rapprochés',
        'allocation':'Répartitions, tantièmes, fonds, avances et mutations vérifiés',
        'comparison':'Comparatif approuvé N−1 et budgets contrôlés, ou premier exercice justifié',
        'works':'Travaux terminés/en cours, financements et cas particuliers examinés',
        'layout':'Les cinq annexes et décomptes ont été relus dans le PDF, sans coupure ni omission',
    },
    'assembly': {
        'identity':'Syndicat, électeurs et mandataires communs identifiés',
        'agenda':'Ordre du jour, textes et majorités relus selon le règlement et chaque objet',
        'attachments':'Pièces/version, annexes et décomptes correspondant au dossier vérifiés',
        'notice':'Dates, modalités de notification, retour postal et courriel contrôlés',
        'correspondence':'Toutes les mentions, pages de vote et rappels du modèle de correspondance relus',
        'layout':'Convocation, correspondance et pouvoir relus dans leurs PDF',
    },
    'minutes': {
        'identity':'Identité du syndicat, bureau et présence certifiée contrôlés',
        'votes':'Textes votés, tours, droits et résultats recalculés et vérifiés',
        'opponents':'Noms et voix des opposants, abstentionnistes et assimilés défaillants contrôlés',
        'signatures':'Signatures et pièces nécessaires identifiées et modalités de conservation vérifiées',
        'notification':'Destinataires, rappel de recours et notifications vérifiés',
        'layout':'PV et feuille de présence relus dans leurs PDF',
    },
}
SOURCES = [
    {'title':'Comptes et annexes — décret n° 2005-240', 'url':'https://www.legifrance.gouv.fr/loda/id/LEGITEXT000006051416/'},
    {'title':'Modèle de correspondance — arrêté du 2 juillet 2020','url':'https://www.legifrance.gouv.fr/loda/id/JORFTEXT000042075372/'},
    {'title':'Convocation, présence et PV — décret du 17 mars 1967','url':'https://www.legifrance.gouv.fr/loda/id/LEGITEXT000006061423/'},
]


def normalize(value):
    return json.loads(json.dumps(value,cls=DjangoJSONEncoder,ensure_ascii=False))


def source(kind, pk):
    if kind not in CHECKLISTS:
        raise ValueError('Type de dossier inconnu.')
    errors=[]
    if kind=='accounting':
        subject=FiscalYear.objects.get(pk=pk)
        closure=YearClosure.objects.filter(year=subject).first()
        data=(closure.snapshot if closure else annexes(subject))
        pack=data.get('regulatory')
        if not pack: raise ValueError('Cet ancien dossier ne contient pas les annexes structurées ; conserver son archive et préparer une version complémentaire contrôlée.')
        errors+=pack['errors']
        if pack.get('version')!=MODEL_VERSION:
            errors.append('Dossier clôturé dans un ancien modèle : il reste conservé sans réécriture, sa validation dans le nouveau modèle exige un dossier complémentaire.')
        if subject.ends_on>timezone.localdate():errors.append('L’exercice doit être terminé avant validation métier de ses comptes.')
        obj={'kind':kind,'model_version':EXPORT_VERSION,'annexes':pack,'individual_allocations':data.get('individual_allocations',[])}
        title='Comptes '+subject.name
        filters={'kind':kind,'year':subject,'workflow__isnull':True}
    else:
        subject=AssemblyWorkflow.objects.select_related('meeting').get(meeting_id=pk)
        from governance.workflow import build_packet
        packet=subject.packet or build_packet(subject)
        obj={'kind':kind,'model_version':EXPORT_VERSION,'packet':packet}
        if kind=='minutes':
            if not subject.minutes.get('resolutions'):
                errors.append('Préparez le PV depuis les votes enregistrés avant sa validation métier.')
            obj['minutes']={k:v for k,v in subject.minutes.items() if k not in ['signed_proof','attendance_proof','signed_on','digest']}
            obj['participants']=subject.participants
        else:
            if not packet.get('building_address'):errors.append('Renseignez l’adresse du ou des immeubles dans la préparation de l’AG.')
            if not packet.get('return_email'):errors.append('Renseignez le courriel de retour des formulaires dans la préparation de l’AG.')
            elif packet.get('return_email'):
                try:validate_email(packet['return_email'])
                except ValidationError:errors.append('Le courriel de retour des formulaires est invalide.')
        if kind=='assembly' and packet.get('account_year',{}):
            annual=packet['account_year'].get('dossier')
            if annual:
                errors+=annual.get('errors',[])
                accounting=source('accounting',packet['account_year']['id'])
                if accounting['payload']['annexes']['source_hash']!=annual['source_hash']:
                    errors.append('Les comptes ont changé depuis la préparation de la convocation : préparer un nouveau dossier avant validation.')
                accounting_status,accounting_review=state(accounting)
                obj['accounting_review']={'status':accounting_status,'decision':accounting_review.pk if accounting_review else None}
                if accounting_status!='approved':errors.append('Faites valider le dossier annuel des comptes avant la convocation qui le présente.')
        for resolution in packet['resolutions']:
            for piece in resolution.get('pieces',[]):
                try:
                    version=evidence(piece['id'])
                    if version.checksum!=piece['checksum']:errors.append('Une pièce jointe ne correspond plus au dossier figé.')
                except (ValueError,Version.DoesNotExist):errors.append('Une pièce de résolution est absente, archivée ou altérée.')
        title=subject.meeting.title
        filters={'kind':kind,'workflow':subject,'year__isnull':True}
    org,_=Organization.objects.get_or_create(pk=1)
    obj['organization']={'name':org.name,'address':org.address,'email':org.email}
    obj['template_hash']=TEMPLATE_HASH
    if not org.name.strip() or not org.address.strip():errors.append('Complétez le nom et l’adresse du syndicat dans Administration → Organisation.')
    obj=normalize(obj)
    return {'subject':subject,'filters':filters,'payload':obj,'source_hash':digest(obj),'errors':list(dict.fromkeys(errors)),'title':title}


def evidence(pk):
    proof=Version.objects.select_related('document').get(pk=pk)
    if proof.document.archived:raise ValueError('Le rapport de validation doit être accessible, pas archivé.')
    h=hashlib.sha256()
    try:
        with proof.file.open('rb') as stream:
            for block in iter(lambda:stream.read(128*1024),b''):h.update(block)
    except (OSError,ValueError):raise ValueError('La pièce de validation est introuvable ou illisible.') from None
    if h.hexdigest()!=proof.checksum:raise ValueError('La pièce de validation est altérée ; déposez une version intacte.')
    return proof


def state(current):
    last=DossierReview.objects.filter(**current['filters']).select_related('proof__document').first()
    status='unreviewed'
    if last:
        if last.verdict=='withdrawn':status='withdrawn'
        elif last.source_hash!=current['source_hash']:status='stale'
        elif last.verdict=='rejected':status='rejected'
        else:
            try:
                proof=evidence(last.proof_id)
                status='approved' if proof.checksum==last.proof_checksum and not current['errors'] else 'stale'
            except ValueError:status='stale'
    return status,last


def save_review(current,data,user):
    kind=current['payload']['kind']
    if data.get('source_hash')!=current['source_hash']:raise ValueError('Le dossier ou le modèle a changé : rechargez et relisez le PDF.')
    verdict=data.get('verdict')
    if verdict not in ['approved','rejected','withdrawn']:raise ValueError('Décision de validation invalide.')
    if verdict=='withdrawn' and not DossierReview.objects.filter(**current['filters']).exists():raise ValueError('Aucune décision à retirer.')
    if verdict=='approved' and current['errors']:raise ValueError('Corrigez les erreurs avant validation : '+' · '.join(current['errors']))
    if data.get('declaration_confirmed') is not True:raise ValueError('Attestez la réalité de la relecture et l’identité du relecteur ; aucune validation automatique.')
    names={}
    for field in ['reviewer','qualification','observations']:
        value=str(data.get(field,'')).strip()
        if not value or len(value)>(10000 if field=='observations' else 200):raise ValueError('Relecteur, qualité et conclusion motivée sont requis.')
        names[field]=value
    day=date.fromisoformat(data['reviewed_on'])
    if day>timezone.localdate():raise ValueError('La relecture doit être effectivement réalisée, pas future.')
    checks=data.get('checks',{})
    if not isinstance(checks,dict) or set(checks)-set(CHECKLISTS[kind]):raise ValueError('Checklist inconnue ou invalide.')
    if any(type(v) is not bool for v in checks.values()):raise ValueError('Les réponses de la checklist doivent être oui/non.')
    if verdict=='approved' and not all(checks.get(k) is True for k in CHECKLISTS[kind]):raise ValueError('Chaque point de contrôle doit être confirmé avant validation.')
    proof=evidence(data['proof'])
    item=DossierReview.objects.create(kind=kind,year=current['subject'] if kind=='accounting' else None,
        workflow=current['subject'] if kind!='accounting' else None,source_hash=current['source_hash'],
        model_version=EXPORT_VERSION,verdict=verdict,reviewed_on=day,checks=checks,
        proof=proof,proof_checksum=proof.checksum,source_snapshot=current['payload'],recorded_by=user,**names)
    from finance.cycle import audit
    audit(user,'dossier.review.'+verdict,item.pk)
    return item
