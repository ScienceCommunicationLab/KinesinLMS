
from django.core.management.base import BaseCommand
from django.db import transaction

from kinesinlms.users.utils import create_default_groups


class Command(BaseCommand):
    """
    Create all default groups in a new KinesinMLS application.
    """

    help = "Create all default groups for new KinesinMLS application."

    def __init__(self, stdout=None, stderr=None, no_color=False):
        super().__init__(stdout=stdout, stderr=stderr, no_color=no_color)

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                create_default_groups()
        except Exception as e:
            self.stdout.write("Error when creating all default groups : {}".format(e))
