from django.apps import AppConfig


# noinspection PyUnresolvedReferences

class CoursesConfig(AppConfig):
    name = 'kinesinlms.course'

    def ready(self):
        import kinesinlms.course.signals
