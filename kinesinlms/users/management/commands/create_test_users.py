from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()

TEST_USERS = [
    {
        "name": "Daniel McQuillen",
        "email": "daniel@mcquilleninteractive.com",
        "username": "daniel"
    }
]

TEST_PASSWORD = 'test1234'


class Command(BaseCommand):
    help = """Creates the standard test users we need on development."""

    def __init__(self, stdout=None, stderr=None, no_color=False):
        super().__init__(stdout=stdout, stderr=stderr, no_color=no_color)

    def handle(self, *args, **options):
        if settings.DJANGO_PIPELINE not in ["LOCAL", "DEVELOPMENT"]:
            raise Exception("This command can only be run locally or on the development server.")

        self.stdout.write(f"CREATING TEST USERS")
        self.stdout.write(f"---------------------------------")

        for user_dict in TEST_USERS:
            name = user_dict.get('name')
            email = user_dict.get('email')
            username = user_dict.get('username')

            if User.objects.filter(username=username).exists():
                self.stdout.write(f" -SKIPPED user {username}. Already exists.")
                continue

            user = User.objects.create_user(name=name,
                                            username=username,
                                            password=TEST_PASSWORD,
                                            email=email)
            user.is_staff = True
            user.save()

            ea, created = EmailAddress.objects.get_or_create(user=user, email=email)
            ea.verified = True
            ea.primary = True
            ea.save()
            self.stdout.write(f" - Created test user {username} for {name}")
