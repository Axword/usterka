from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class UsterkaUserAdmin(UserAdmin):
    list_display = ('email', 'display_name', 'entra_oid', 'is_active', 'is_staff')
    search_fields = ('email', 'display_name', 'entra_oid')
    fieldsets = (*UserAdmin.fieldsets, ('Microsoft', {'fields': ('display_name', 'entra_oid', 'entra_tenant_id')}))
