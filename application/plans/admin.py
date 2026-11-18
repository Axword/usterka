from django.contrib import admin

from .models import Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'width', 'height', 'created_at')
    search_fields = ('name', 'project__name')
