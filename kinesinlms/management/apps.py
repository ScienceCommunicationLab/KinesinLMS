from django.apps import AppConfig


class ManagementConfig(AppConfig):
    name = 'kinesinlms.management'

    def ready(self):
        import kinesinlms.management.signals # noqa
