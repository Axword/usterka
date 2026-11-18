from django.contrib import admin
from django.urls import path

from .api import api

admin.site.site_header = 'Usterki na planie - administracja'
admin.site.site_title = 'Usterki na planie'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
