import contextlib

from django.apps import AppConfig


class UsersAppConfig(AppConfig):
    name = "kinesinlms.users"
    verbose_name = "Users"

    def ready(self):
        with contextlib.suppress(ImportError):
            import kinesinlms.users.signals  # noqa F401
