from django.contrib import admin

from .models import Defect, DefectEvent, Photo


class PhotoInline(admin.TabularInline):
    model = Photo
    extra = 0
    readonly_fields = ('kind', 'image', 'width', 'height')


@admin.register(Defect)
class DefectAdmin(admin.ModelAdmin):
    list_display = ('no', 'project', 'plan', 'type', 'status', 'due_mode', 'due_date')
    list_filter = ('status', 'type', 'project__organization')
    search_fields = ('description', 'project__name')
    inlines = [PhotoInline]


@admin.register(DefectEvent)
class DefectEventAdmin(admin.ModelAdmin):
    list_display = ('defect', 'action', 'user', 'created_at')
    readonly_fields = ('defect', 'user', 'action', 'changes', 'created_at')
