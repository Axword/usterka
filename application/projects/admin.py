from django.contrib import admin

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'address', 'inspection_date', 'updated_at')
    list_filter = ('organization',)
    search_fields = ('name', 'address', 'investor', 'contractor')
