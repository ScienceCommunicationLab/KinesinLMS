from django.core.management.base import BaseCommand

from kinesinlms.course.models import CourseUnit
from kinesinlms.learning_library.models import Block, LibraryItem, LibraryItemType


class Command(BaseCommand):
    help = "Add all existing units and nodes to learning library."

    def __init__(self, stdout=None, stderr=None, no_color=False):
        super().__init__(stdout=stdout, stderr=stderr, no_color=no_color)

    def handle(self, *args, **options):
        self.create_course_units()
        self.create_blocks()

    def create_course_units(self):
        course_units = CourseUnit.objects.all()
        for course_unit in course_units:
            library_item, created = LibraryItem.objects.get_or_create(course_unit=course_unit,
                                                                      type=LibraryItemType.UNIT.name)
            if created:
                self.stdout.write(f"Created library item  {library_item} for course unit {course_unit}")

    def create_blocks(self):
        blocks = Block.objects.all()
        for block in blocks:
            library_item, created = LibraryItem.objects.get_or_create(block=block,
                                                                      type=LibraryItemType.BLOCK.name)

            if created:
                self.stdout.write(f"Created library item {library_item} for block unit {block}")
