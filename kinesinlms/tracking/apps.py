from django.apps import AppConfig


# noinspection PyUnresolvedReferences
class TrackingConfig(AppConfig):
    name = 'kinesinlms.tracking'

    def ready(self):
        import kinesinlms.tracking.signals
