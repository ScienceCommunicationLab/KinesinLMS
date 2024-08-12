import logging

from django.contrib.postgres.search import SearchVector
from django.db.models.signals import post_save
from django.dispatch import receiver

from kinesinlms.learning_library.constants import BlockType
from kinesinlms.learning_library.models import Block

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Block)
def handle_block_saved(sender, instance: Block, **kwargs):  # noqa: F841
    """
    Update Block search vectors when Block is saved.

    Args:
        sender:
        instance:
        kwargs:

    Returns:
        ( nothing )

    """

    try:
        # Update the text search vector fields...
        block = Block.objects.filter(id=instance.id)
        search_vectors = SearchVector('display_name', weight='A')
        if instance.type == BlockType.VIDEO.name:
            search_vectors += SearchVector('html_content', weight='B') + SearchVector('json_content', weight='C')
        else:
            search_vectors += SearchVector('html_content', weight='B')
        block.update(search_vector=search_vectors)
    except Exception as e:
        logger.exception(f"handle_block_saved() post save signal: Could not update search vector "
                         f"fields for block {instance} error: {e}")
