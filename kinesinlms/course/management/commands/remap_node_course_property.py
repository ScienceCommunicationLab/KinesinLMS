from django.core.management.base import BaseCommand

from kinesinlms.learning_library.models import Block


class Command(BaseCommand):
    help = "Create groups needed for KinesinLMS."

    def __init__(self, stdout=None, stderr=None, no_color=False):
        super().__init__(stdout=stdout, stderr=stderr, no_color=no_color)

    def handle(self, *args, **options):
        self.remap_block_course_property()

    def remap_block_course_property(self):
        """
        Goes through all nodes and makes sure their Course property is set to the right course.
        Remember that the Node's 'course' property is a convenience relationship (and not really
        normalized, it just makes various lookup tasks much easier).

        :return:
        """

        blocks = Block.objects.all()
        for block in blocks:
            was_empty = block.course is None

            # TODO: Set block.course to correct course.

            if was_empty:
                self.stdout.write("{} was empty but now assigned to course {}".format(block, block.course))
            block.save()

