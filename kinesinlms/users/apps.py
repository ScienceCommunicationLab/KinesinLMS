from django.apps import AppConfig


class UsersAppConfig(AppConfig):

    name = "kinesinlms.users"
    verbose_name = "Users"

    def ready(self):
        try:
            import kinesinlms.users.signals  # noqa F401
        except ImportError:
            pass
