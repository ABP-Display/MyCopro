"""Private, paginated statements: the owner always comes from the session."""
import csv
from datetime import date
from decimal import Decimal
from io import BytesIO, StringIO
from django.db.models import Sum
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_GET
from core.access import member_required, allow_former_owner
from finance.views import errors
from finance.models import Organization

MAX_EXPORT = 10000


def total(query):
    values = query.aggregate(d=Sum('debit'), c=Sum('credit'))
    return (values['d'] or Decimal(0)), (values['c'] or Decimal(0))


def statement(owner, params, paginate=True):
    from .views import owner_lines, owner_balance
    today = timezone.localdate()
    start = date.fromisoformat(params['from']) if params.get('from') else None
    end = date.fromisoformat(params['to']) if params.get('to') else today
    if end > today or (start and (start > end)):
        raise ValueError('Choisissez une période dans l’ordre chronologique, jusqu’à aujourd’hui au plus tard.')
    page = int(params.get('page', 1)) if paginate else 1
    if page < 1:
        raise ValueError('Numéro de page invalide.')
    query = owner_lines(owner).filter(entry__date__lte=end)
    opening = Decimal(0)
    if start:
        d, c = total(query.filter(entry__date__lt=start))
        opening = d-c
        query = query.filter(entry__date__gte=start)
    d, c = total(query)
    count = query.count()
    pages = max(1, (count+49)//50)
    if paginate and page > pages:
        raise ValueError('Cette page n’existe pas.')
    if not paginate and count > MAX_EXPORT:
        raise ValueError('Plus de 10 000 mouvements : réduisez la période avant de télécharger le relevé.')
    rows = query.reverse()[(page-1)*50:page*50] if paginate else query
    return {
        'balance': str(owner_balance(owner)), 'date': str(today),
        'from': str(start) if start else '', 'to': str(end),
        'opening_balance': str(opening), 'closing_balance': str(opening+d-c),
        'total_debit': str(d), 'total_credit': str(c),
        'count': count, 'page': page, 'pages': pages, 'page_size': 50,
        'rows': [{'date': str(line.entry.date), 'label': line.entry.label,
                  'debit': str(line.debit), 'credit': str(line.credit)} for line in rows],
        'note': 'Solde cumulé des comptes 450, hors reports déjà repris dans l’historique. Un solde débiteur ne suffit pas à établir un retard de paiement.',
    }


def statement_pdf(owner, data):
    from documents.pdf import p, table, money, SimpleDocTemplate, A4, Spacer
    org = Organization.objects.filter(pk=1).first()
    stream = BytesIO()
    doc = SimpleDocTemplate(stream, pagesize=A4, leftMargin=35, rightMargin=35,
                            topMargin=35, bottomMargin=48, title='Relevé individuel', author='Copro.')
    story = [p(org.name if org else 'Copro.', 'Heading2'), p(org.address if org else ''),
             p('Relevé individuel de copropriétaire', 'Heading1'), p(str(owner)), p(owner.email),
             p('Période : '+(data['from'] or 'depuis l’origine')+' au '+data['to']),
             p('Édité le '+data['date']+' · Montants en euros'), Spacer(1,12),
             p('Solde au début de la période : '+money(data['opening_balance'])+' €')]
    width = A4[0]-70
    story.append(table(['Date', 'Libellé', 'Débit (€)', 'Crédit (€)'],
        [[r['date'], r['label'], money(r['debit']), money(r['credit'])] for r in data['rows']],
        [width*.16, width*.50, width*.17, width*.17], (2,3)))
    story.extend([Spacer(1,12), p('Totaux de la période : débit '+money(data['total_debit'])+' € ; crédit '+money(data['total_credit'])+' €'),
                  p('Solde en fin de période : '+money(data['closing_balance'])+' €','Heading2'),
                  p('Un solde positif est débiteur (somme due au syndicat), un solde négatif est créditeur (avance ou excédent).'), p(data['note'])])
    def footer(canvas, document):
        canvas.setFont('Copro',7)
        canvas.drawString(35,24,'Copro. · Relevé personnel confidentiel · Page '+str(document.page))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return stream.getvalue()


def csv_text(value):
    text = str(value)
    return "'"+text if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t','\r','\n')) else text


@require_GET
@member_required
@allow_former_owner
@errors
def personal_account(request):
    owner = getattr(request.user,'owner_profile',None)
    if owner is None:
        return JsonResponse({'error':'Compte copropriétaire requis.'},status=403)
    return JsonResponse(statement(owner,request.GET))


@require_GET
@member_required
@allow_former_owner
@errors
def export(request):
    owner = getattr(request.user,'owner_profile',None)
    if owner is None:
        return JsonResponse({'error':'Compte copropriétaire requis.'},status=403)
    kind = request.GET.get('format','pdf')
    if kind not in ('pdf','csv'):
        raise ValueError('Formats disponibles : PDF et CSV.')
    data = statement(owner,request.GET,paginate=False)
    if kind == 'pdf':
        response = HttpResponse(statement_pdf(owner,data),content_type='application/pdf')
    else:
        stream = StringIO(); writer = csv.writer(stream,delimiter=';')
        writer.writerow(['Date','Libellé','Débit EUR','Crédit EUR'])
        for row in data['rows']:
            writer.writerow([row['date'],csv_text(row['label']),row['debit'],row['credit']])
        writer.writerow(['','Solde initial',data['opening_balance'],''])
        writer.writerow(['','Total période',data['total_debit'],data['total_credit']])
        writer.writerow(['','Solde final',data['closing_balance'],''])
        response = HttpResponse('\ufeff'+stream.getvalue(),content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="mon-releve.'+kind+'"'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
