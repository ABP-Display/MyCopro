import uuid
from pathlib import Path
from django.conf import settings
from django.db import models


def asset_path(instance, filename):
    return f"documents/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


class Folder(models.Model):
    name = models.CharField(max_length=150, unique=True)
    class Meta:
        ordering = ["name"]


class Document(models.Model):
    title = models.CharField(max_length=150)
    folder = models.ForeignKey(Folder, on_delete=models.PROTECT, null=True, blank=True)
    published = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)
    current = models.OneToOneField("Version", on_delete=models.PROTECT, null=True, related_name="current_for")
    class Meta:
        ordering = ["title", "id"]


class Version(models.Model):
    document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name="versions")
    file = models.FileField(upload_to=asset_path, max_length=200)
    filename = models.CharField(max_length=200)
    size = models.PositiveIntegerField()
    content_type = models.CharField(max_length=100)
    checksum = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    class Meta:
        ordering = ["-id"]


class DossierReview(models.Model):
    """Append-only declarations; a decision always refers to one exact document source."""
    kind = models.CharField(max_length=12, choices=[('accounting','Comptes'),('assembly','Convocation'),('minutes','Procès-verbal')])
    year = models.ForeignKey('finance.FiscalYear', on_delete=models.PROTECT, null=True)
    workflow = models.ForeignKey('governance.AssemblyWorkflow', on_delete=models.PROTECT, null=True)
    source_hash = models.CharField(max_length=64)
    model_version = models.CharField(max_length=40)
    verdict = models.CharField(max_length=12, choices=[('approved','Validé'),('rejected','À corriger'),('withdrawn','Validation retirée')])
    reviewer = models.CharField(max_length=200)
    qualification = models.CharField(max_length=200)
    reviewed_on = models.DateField()
    checks = models.JSONField(default=dict)
    observations = models.TextField(max_length=10000)
    proof = models.ForeignKey(Version, on_delete=models.PROTECT)
    proof_checksum = models.CharField(max_length=64)
    source_snapshot = models.JSONField()
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-id']
        constraints = [models.CheckConstraint(condition=(models.Q(kind='accounting',year__isnull=False,workflow__isnull=True) | models.Q(kind__in=['assembly','minutes'],year__isnull=True,workflow__isnull=False)),name='dossier_review_subject')]
