from django.contrib import admin

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('filename', 'project', 'kind', 'document_date', 'sharepoint_status', 'created_at')
    list_filter = ('kind', 'sharepoint_status')
