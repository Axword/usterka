from django.db import models

from core.models import TimeStampedModel
from organizations.models import Organization

ACTIVE_STATUSES = {'active', 'trialing', 'past_due'}


class Subscription(TimeStampedModel):
    """Plan organizacji. Brak rekordu = plan „free”."""

    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name='subscription')
    plan = models.CharField(max_length=20, default='free')
    status = models.CharField(max_length=30, default='active')
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    is_demo = models.BooleanField('symulacja (bez płatności)', default=False)

    def __str__(self):
        return f'{self.organization} - {self.plan} ({self.status})'

    @property
    def effective_plan(self) -> str:
        return self.plan if self.status in ACTIVE_STATUSES else 'free'
