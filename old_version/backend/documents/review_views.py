from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from core.views import payload
from council.views import council_required
from council.access import can, is_manager, CONTROL
from finance.idempotency import idempotent
from finance.models import FiscalYear
from governance.models import AssemblyWorkflow
from .models import DossierReview, Version
from . import review


def history(current):
    return list(DossierReview.objects.filter(**current['filters']).values(
        'id','verdict','reviewer','qualification','reviewed_on','observations','proof_id',
        'source_hash','model_version','created_at','recorded_by_id','checks'))


@require_http_methods(['GET','POST'])
@council_required
@idempotent
def validation(request, kind, pk):
    allowed=is_manager(request.user) or can(request.user,CONTROL)
    if request.method=='POST':
        if not allowed:raise PermissionError('Seuls le syndic et le contrôleur des comptes peuvent enregistrer une relecture.')
        with transaction.atomic():
            # Match the assembly workflow lock order: workflow then financial years.
            if kind!='accounting':AssemblyWorkflow.objects.select_for_update().get(meeting_id=pk)
            list(FiscalYear.objects.select_for_update().order_by('pk'))
            current=review.source(kind,pk)
            item=review.save_review(current,payload(request),request.user)
        return JsonResponse({'id':item.pk},status=201)
    current=review.source(kind,pk)
    status,_=review.state(current)
    versions=Version.objects.filter(document__archived=False).select_related('document') if allowed else Version.objects.none()
    return JsonResponse({'title':current['title'],'source_hash':current['source_hash'],
        'model_version':review.EXPORT_VERSION,'status':status,'errors':current['errors'],
        'checks':review.CHECKLISTS[kind],'can_review':allowed,'history':history(current),
        'sources':review.SOURCES,'versions':[{'id':v.pk,'title':v.document.title,'filename':v.filename} for v in versions]})


@require_http_methods(['GET'])
@council_required
def export(request, kind, pk, document):
    from .pdf import render
    with transaction.atomic():
        if kind!='accounting':AssemblyWorkflow.objects.select_for_update().get(meeting_id=pk)
        list(FiscalYear.objects.select_for_update().order_by('pk'))
        current=review.source(kind,pk)
        status,last=review.state(current)
        official=request.GET.get('official')=='1'
        if official and status!='approved':raise ValueError('Édition validée indisponible : une relecture métier actuelle, documentée et sans erreur est nécessaire.')
        data=render(current,document,last if official else None)
    response=HttpResponse(data,content_type='application/pdf')
    response['Content-Disposition']=f'attachment; filename="copro-{kind}-{pk}-{document}-'+('valide' if official else 'projet')+'.pdf"'
    response['X-Content-Type-Options']='nosniff'
    return response
