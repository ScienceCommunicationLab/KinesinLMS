from django.core.management.base import BaseCommand

from django.contrib.postgres.search import SearchVector
from kinesinlms.learning_library.models import Block, BlockType


class Command(BaseCommand):
    help = "Refresh the search vectors for all blocks."

    def __init__(self, stdout=None, stderr=None, no_color=False):
        super().__init__(stdout=stdout, stderr=stderr, no_color=no_color)

    def handle(self, *args, **options):

        self.stdout.write("Updating search vectors for all blocks...")

        for block in Block.objects.all():
            self.stdout.write(f"  - block {block}")
            search_vectors = SearchVector('display_name', weight='A')
            if block.type == BlockType.VIDEO.name:
                search_vectors += SearchVector('html_content', weight='B') + SearchVector('json_content', weight='C')
            else:
                search_vectors += SearchVector('html_content', weight='B')
            Block.objects.filter(block.id).update(search_vector=search_vectors)
