from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    name = 'projects'
    verbose_name = 'Inwestycje'

    def ready(self):
        from core import signals  # noqa: F401
