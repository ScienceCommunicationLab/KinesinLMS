import logging

from kinesinlms.learning_library.models import Block, BlockLearningObjective, LearningObjective
from kinesinlms.speakers.models import Speaker

logger = logging.getLogger(__name__)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# HELPER Methods
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def save_learning_objectives(los_input: str, block: Block):
    """
    Given user's input from an edit block form, add or remove
    LearningObjectives to this block.

    Input should be a list of LearningObjectives slugs, separated by commas.
    """
    if los_input:
        lo_slugs = los_input.split(",")
        lo_slugs = [item.strip().lower() for item in lo_slugs]

        # Remove any currently attached LOs no longer in input
        for learning_objective in block.learning_objectives.all():
            if learning_objective.slug not in lo_slugs:
                lo_links = BlockLearningObjective.objects.filter(block=block,
                                                                 learning_objective=learning_objective)
                lo_links.delete()

        # Add newly attached LOs
        for lo_slug in lo_slugs:
            lo = LearningObjective.objects.get(slug=lo_slug)
            block_lo, created = BlockLearningObjective.objects.get_or_create(block=block,
                                                                             learning_objective=lo)
            if created:
                logger.info(f"Adding LO {lo_slug}")
    else:
        # No input so assumption is no LearningObjectives
        # should be assigned to this block.
        if hasattr(block, 'block_learning_objectives'):
            block.block_learning_objectives.all().delete()


def save_block_speakers(speakers_input: str, block: Block):
    """
    Given user's input from an edit block form, add or remove
    speakers to this block.

    Input should be a list of speaker slugs, separated by commas.
    """
    if speakers_input:
        speaker_slugs = speakers_input.split(",")
        speaker_slugs = [item.strip().lower() for item in speaker_slugs]

        # Remove any currently attached speakers no longer in input
        for speaker in block.speakers.all():
            if speaker.slug not in speaker_slugs:
                block.speakers.remove(speaker)

        # Add newly attached speakers
        for speaker_slug in speaker_slugs:
            speaker = Speaker.objects.get(slug=speaker_slug)
            block.speakers.add(speaker)
    else:
        # No input so assumption is no Speakers
        # should be assigned to this block.
        if hasattr(block, 'speakers'):
            block.speakers.clear()
