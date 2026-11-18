from django.conf import settings
from django.db import models

from core.models import TimeStampedModel, UUIDModel
from organizations.models import Organization

REQUIRED_FIELDS = ['name', 'address', 'investor', 'contractor', 'inspection_date', 'author']


def logo_path(instance, filename):
    return f'org/{instance.organization_id}/projects/{instance.id}/logo/{filename}'


class Project(UUIDModel, TimeStampedModel):
    """Inwestycja (obiekt odbierany). Wszystkie pola poza logo są wymagane do dodania planu."""

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField('nazwa inwestycji', max_length=300)
    address = models.CharField('adres', max_length=300, blank=True)
    investor = models.CharField('inwestor', max_length=300, blank=True)
    contractor = models.CharField('wykonawca', max_length=300, blank=True)
    inspection_date = models.DateField('data przeglądu', null=True, blank=True)
    author = models.CharField('sporządzający protokół', max_length=200, blank=True)
    logo = models.FileField(upload_to=logo_path, max_length=500, blank=True)
    next_no = models.PositiveIntegerField('następny numer usterki', default=1)
    report_settings = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name

    @property
    def is_complete(self) -> bool:
        return all(getattr(self, f) for f in REQUIRED_FIELDS)
