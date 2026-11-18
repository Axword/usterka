from django.conf import settings
from django.db import models

from core.models import TimeStampedModel, UUIDModel

DEFAULT_DEFECT_TYPES = ['Budowlana', 'Sanitarna', 'Elektryczna', 'Instalacje budynkowe', 'Meble/wyposażenie', 'Inna']


ROLE_CHOICES = [('admin', 'Administrator'), ('inspector', 'Inspektor'), ('viewer', 'Podgląd')]


def default_defect_types():
    return list(DEFAULT_DEFECT_TYPES)


class Organization(UUIDModel, TimeStampedModel):
    """Firma korzystająca z aplikacji. Jedna dzierżawa Microsoft = jedna organizacja."""

    name = models.CharField('nazwa', max_length=200)
    entra_tenant_id = models.CharField('Entra tenant id', max_length=64, unique=True, null=True, blank=True)
    email_domain = models.CharField('domena e-mail', max_length=200, blank=True)
    defect_types = models.JSONField('rodzaje usterek', default=default_defect_types)
    # SharePoint: domyślne miejsce zapisu raportów
    sp_site_url = models.URLField('adres witryny SharePoint', blank=True)
    sp_library = models.CharField('biblioteka dokumentów', max_length=200, blank=True)
    sp_folder = models.CharField('folder', max_length=300, default='Usterki/{inwestycja}', blank=True)

    def __str__(self):
        return self.name


class Invitation(UUIDModel, TimeStampedModel):
    """Zaproszenie do organizacji. W bazie jest tylko skrót tokenu: wyciek bazy nie ujawnia działających linków."""

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='invitations')
    email = models.EmailField('e-mail zaproszonej osoby')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='inspector')
    token_hash = models.CharField(max_length=64, unique=True)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Zaproszenie {self.email} do {self.organization}'

    @property
    def is_pending(self) -> bool:
        from django.utils import timezone

        return self.accepted_at is None and self.expires_at > timezone.now()


class Membership(TimeStampedModel):
    ROLES = ROLE_CHOICES

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=ROLES, default='inspector')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'organization'], name='unique_membership')]

    def __str__(self):
        return f'{self.user} @ {self.organization} ({self.role})'
