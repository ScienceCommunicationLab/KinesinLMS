from django.apps import AppConfig


# noinspection PyUnresolvedReferences
class LearningLibraryConfig(AppConfig):
    name = 'kinesinlms.learning_library'

    def ready(self):
        import kinesinlms.learning_library.signals
