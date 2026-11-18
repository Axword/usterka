from django.contrib import admin

from .models import Membership, Organization


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    autocomplete_fields = ['user']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'email_domain', 'entra_tenant_id', 'sp_site_url')
    search_fields = ('name', 'email_domain', 'entra_tenant_id')
    inlines = [MembershipInline]
