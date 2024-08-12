from django.core.management.base import BaseCommand

from kinesinlms.sits.models import SimpleInteractiveToolSubmission


class Command(BaseCommand):
    help = "Normalizes the 'status' property of SITs in July 2023 after the status bug was fixed."

    def __init__(self, stdout=None, stderr=None, no_color=False):
        super().__init__(stdout=stdout, stderr=stderr, no_color=no_color)

    def handle(self, *args, **options):
        sit_submissions = SimpleInteractiveToolSubmission.objects.all()
        for ss in sit_submissions:
            ss.set_status()
            print(f"Setting status for SIT submission {ss} to {ss.status}")



