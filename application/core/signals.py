"""Usuwanie plików z magazynu razem z rekordami."""

import logging

from django.db.models import FileField
from django.db.models.signals import post_delete
from django.dispatch import receiver

log = logging.getLogger(__name__)


@receiver(post_delete)
def delete_files(sender, instance, **kwargs):
    if sender._meta.app_label not in {'projects', 'plans', 'defects', 'reports'}:
        return
    for field in sender._meta.fields:
        if isinstance(field, FileField):
            f = getattr(instance, field.name)
            if f:
                try:
                    f.storage.delete(f.name)
                except OSError:
                    log.warning('Nie udało się usunąć pliku %s', f.name)
