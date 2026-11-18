from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Osoba logująca się kontem Microsoft (entra_oid) albo - lokalnie - samym e-mailem."""

    email = models.EmailField('e-mail', unique=True)
    display_name = models.CharField('imię i nazwisko', max_length=200, blank=True)
    entra_oid = models.CharField('Entra object id', max_length=64, unique=True, null=True, blank=True)
    entra_tenant_id = models.CharField('Entra tenant id', max_length=64, blank=True)
    email_verified = models.BooleanField('e-mail potwierdzony', default=False)

    def __str__(self):
        return self.display_name or self.email
