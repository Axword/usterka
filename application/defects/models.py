from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import TimeStampedModel, UUIDModel
from plans.models import Plan
from projects.models import Project

UNIT = [MinValueValidator(0.0), MaxValueValidator(1.0)]


class Defect(UUIDModel, TimeStampedModel):
    """Usterka = pinezka na planie. x, y są znormalizowane (0..1) względem obrazu planu."""

    STATUS = [('open', 'Otwarta'), ('fixed', 'Usunięta')]
    DUE = [('umowa', 'Zgodnie z umową'), ('data', 'Data')]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='defects')
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='defects')
    no = models.PositiveIntegerField('numer')
    x = models.FloatField(validators=UNIT)
    y = models.FloatField(validators=UNIT)
    type = models.CharField('rodzaj', max_length=100)
    type_other = models.CharField('rodzaj - doprecyzowanie', max_length=200, blank=True)
    description = models.TextField('opis')
    due_mode = models.CharField('termin', max_length=10, choices=DUE)
    due_date = models.DateField('termin usunięcia', null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default='open')
    fixed_date = models.DateField('data usunięcia', null=True, blank=True)
    zoom = models.FloatField('zasięg wycinka', default=0.3, validators=[MinValueValidator(0.1), MaxValueValidator(0.6)])
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')

    class Meta:
        ordering = ['no']
        constraints = [models.UniqueConstraint(fields=['project', 'no'], name='unique_defect_no_per_project')]

    def __str__(self):
        return f'Usterka nr {self.no}'


def photo_path(instance, filename):
    d = instance.defect
    return f'org/{d.project.organization_id}/projects/{d.project_id}/photos/{filename}'


class Photo(UUIDModel, TimeStampedModel):
    KINDS = [('before', 'Przed usunięciem'), ('after', 'Po usunięciu')]

    defect = models.ForeignKey(Defect, on_delete=models.CASCADE, related_name='photos')
    kind = models.CharField(max_length=10, choices=KINDS)
    image = models.FileField(upload_to=photo_path, max_length=500)
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    order = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')

    class Meta:
        ordering = ['kind', 'order', 'created_at']

    def __str__(self):
        return f'{self.get_kind_display()} - {self.defect}'


class DefectEvent(models.Model):
    """Historia zmian - kto i kiedy co zmienił (spory z wykonawcą, audyt)."""

    defect = models.ForeignKey(Defect, on_delete=models.CASCADE, related_name='events')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    action = models.CharField(max_length=30)
    changes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.defect}: {self.action}'
