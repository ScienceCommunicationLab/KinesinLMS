from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a sample course to demonstrate system functionality."

    def handle(self, *args, **options):
        self.stdout.write("Creating sample course...")

