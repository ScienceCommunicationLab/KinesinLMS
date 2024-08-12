"""

Factory classes for creating blocks.

These are runtime (not test) factory methods for creating new blocks. They should
set up the block in the database, and set the necessary properties and linkages
before returning the Block.

The factory classes are pretty slim at the moment, but the idea is they may
grow to do some initial setup as the blocks become more complex.

# FACTORIES FOR DIFFERENT BLOCKS (using factory-boy)

"""
import logging

from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyText

from kinesinlms.assessments.models import Assessment
from kinesinlms.external_tools.models import ExternalToolView
from kinesinlms.learning_library.constants import BlockType
from kinesinlms.learning_library.models import Block
from kinesinlms.sits.models import SimpleInteractiveTool

logger = logging.getLogger(__name__)


# Factories for models associated with Blocks...
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class AssessmentFactory(DjangoModelFactory):
    graded = True

    class Meta:
        model = Assessment


class SimpleInteractiveToolFactory(DjangoModelFactory):
    class Meta:
        model = SimpleInteractiveTool

    slug = FuzzyText(prefix="simple-interactive-tool-")


class ExternalToolViewFactory(DjangoModelFactory):
    class Meta:
        model = ExternalToolView


# Factories for Block instances
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class SurveyBlockFactory(DjangoModelFactory):
    class Meta:
        model = Block

    type = BlockType.SURVEY.name


class ForumTopicBlockFactory(DjangoModelFactory):
    class Meta:
        model = Block

    type = BlockType.FORUM_TOPIC.name


class AssessmentBlockFactory(DjangoModelFactory):
    class Meta:
        model = Block

    type = BlockType.ASSESSMENT.name

    # Don't need to create related Assessment instance
    # here, the builder will create it.


class VideoBlockFactory(DjangoModelFactory):
    class Meta:
        model = Block

    type = BlockType.VIDEO.name


class HTMLContentBlockFactory(DjangoModelFactory):
    class Meta:
        model = Block

    type = BlockType.HTML_CONTENT.name


class FileResourceBlockFactory(DjangoModelFactory):
    class Meta:
        model = Block

    type = BlockType.FILE_RESOURCE.name


class SimpleInteractiveToolBlockFactory(DjangoModelFactory):
    class Meta:
        model = Block

    type = BlockType.SIMPLE_INTERACTIVE_TOOL.name


class ExternalToolViewBlockFactory(DjangoModelFactory):
    class Meta:
        model = Block

    type = BlockType.EXTERNAL_TOOL_VIEW.name
