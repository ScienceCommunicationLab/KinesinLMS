from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from kinesinlms.users.models import UserSettings

User = get_user_model()


class Command(BaseCommand):
    help = """Creatings a 'settings' instance for all existing users that do not already have one."""

    def __init__(self, stdout=None, stderr=None, no_color=False):
        super().__init__(stdout=stdout, stderr=stderr, no_color=no_color)

    def handle(self, *args, **options):
        for user in User.objects.all():
            if not hasattr(user, 'settings'):
                print(f"Creating settings for user : {user}")
                UserSettings.objects.create(user=user, enable_badges=True)

