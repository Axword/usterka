from django.db import models

from core.models import TimeStampedModel, UUIDModel
from projects.models import Project


def plan_path(instance, filename):
    return f'org/{instance.project.organization_id}/projects/{instance.project_id}/plans/{filename}'


class Plan(UUIDModel, TimeStampedModel):
    """Podkład (rzut). PDF jest renderowany do obrazu w przeglądarce, tu trafia gotowy JPEG/PNG."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='plans')
    name = models.CharField('nazwa', max_length=200)
    image = models.FileField(upload_to=plan_path, max_length=500)
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    source_filename = models.CharField(max_length=300, blank=True)
    source_page = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return self.name
