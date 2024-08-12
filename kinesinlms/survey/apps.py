from django.apps import AppConfig


# noinspection PyUnresolvedReferences
class SurveyConfig(AppConfig):
    name = 'kinesinlms.survey'

    def ready(self):
        import kinesinlms.survey.signals
