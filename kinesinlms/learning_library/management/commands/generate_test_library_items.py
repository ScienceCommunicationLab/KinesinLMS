from django.core.management.base import BaseCommand

from kinesinlms.course.tests.factories import BlockFactory, CourseFactory
from kinesinlms.learning_library.constants import BlockType
from kinesinlms.learning_library.models import LibraryItem, LibraryItemType
from faker import Faker # noqa

fake = Faker()


class Command(BaseCommand):
    help = "Generate test items for the Learning Library."

    def __init__(self, stdout=None, stderr=None, no_color=False):
        super().__init__(stdout=stdout, stderr=stderr, no_color=no_color)

    def handle(self, *args, **options):
        self.generate_test_blocks()
        self.generate_test_course_units()

    def generate_test_blocks(self):
        """
        Generate some stand-alone blocks that can appear in
        the Learning Library under "Blocks".
        """
        for i in range(1, 100):
            block = BlockFactory.create(
                display_name=f"Test Block {i}",
                short_description=fake.text(),
                html_content=f"<p>{fake.text()}</p>",
                type=BlockType.VIDEO.name,
                json_content={
                    "header": "Some video header",
                    "video_id": "wDchsz8nmbo"
                }
            )
            LibraryItem.objects.create(
                block=block,
                type=LibraryItemType.BLOCK.name
            )

    def generate_test_course_units(self):
        """
        Generate some course units that can appear in the
        Learning Library under "Units".
        """
        for i in range(1, 10):
            course = CourseFactory.create(
                display_name=f"Test Course {i}"
            )
            
            for course_unit in course.course_units.all():
                LibraryItem.objects.create(
                    course_unit=course_unit,
                    type=LibraryItemType.UNIT.name
                )
