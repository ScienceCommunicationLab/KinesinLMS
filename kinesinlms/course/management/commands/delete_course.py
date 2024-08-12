import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from kinesinlms.course.delete_utils import delete_course
from kinesinlms.course.models import Course

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Completely delete a course, including catalog description, nodes, units and assessments."

    def __init__(self, stdout=None, stderr=None, no_color=False):
        super().__init__(stdout=stdout, stderr=stderr, no_color=no_color)

    def add_arguments(self, parser):
        parser.add_argument('token', type=str)
        parser.add_argument('--all',
                            action='store_true',
                            help='Delete *all* related records, including student progress against the course.')

    def handle(self, *args, **options):
        token = options['token']
        self.stdout.write(f"Delete course {token}")
        slug, run = token.split("_")

        confirm = self.boolean_input(question=f"Are you sure you want to delete course {token}? (y/n): ")
        if not confirm:
            self.stdout.write("Cancelling command.")
            exit()

        try:
            course = Course.objects.get(slug=slug, run=run)
        except Course.DoesNotExist:
            self.stdout.write(f"NO ACTION! Can't find course with token {token}")
            return

        with transaction.atomic():
            delete_course(course, delete_all_progress=options['all'])
            self.stdout.write(f"Course {token} deleted!")

    # This method is from Django django/db/migrations/questioner.py
    def boolean_input(self, question, default=None):
        result = input("%s " % question)
        if not result and default is not None:
            return default
        while len(result) < 1 or result[0].lower() not in "yn":
            result = input("Please answer y (yes) or n (no): ")
        return result[0].lower() == "y"

