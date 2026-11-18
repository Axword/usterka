from django.conf import settings
from django.db import models

from core.models import TimeStampedModel, UUIDModel
from projects.models import Project


def report_path(instance, filename):
    return f'org/{instance.project.organization_id}/projects/{instance.project_id}/reports/{filename}'


class Report(UUIDModel, TimeStampedModel):
    """Wygenerowany protokół (PDF/DOCX). Generuje go przeglądarka, serwer archiwizuje i wysyła do SharePoint."""

    KINDS = [('pdf', 'PDF'), ('docx', 'Word')]
    SP_STATUS = [('none', 'Nie wysyłano'), ('ok', 'Zapisano'), ('error', 'Błąd')]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='reports')
    kind = models.CharField(max_length=5, choices=KINDS)
    filename = models.CharField(max_length=300)
    file = models.FileField(upload_to=report_path, max_length=500)
    size = models.PositiveIntegerField(default=0)
    document_date = models.DateField()
    defect_filter = models.CharField(max_length=10, default='all')
    defects_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    sharepoint_status = models.CharField(max_length=10, choices=SP_STATUS, default='none')
    sharepoint_url = models.URLField(max_length=1000, blank=True)
    sharepoint_path = models.CharField(max_length=1000, blank=True)
    sharepoint_error = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
