"""
Builders for creating blocks (using factories).

This whole set of builders, which then rely on factories,
kind of feels like overkill. But my guess is that the
process of building a block is going to grow more complex
as we add more block types and more related models, and each
builder might end up using a different set of factories.

And then again, it might just be this is stupid.

"""

import logging
from abc import abstractmethod
from typing import List, Optional, Tuple

from kinesinlms.course.constants import CourseUnitType
from kinesinlms.course.models import CourseUnit
from kinesinlms.forum.models import ForumTopic
from kinesinlms.learning_library.constants import AssessmentType, BlockType

# FACTORIES FOR DIFFERENT BLOCKS (using factory-boy)
from kinesinlms.learning_library.factory import (
    AssessmentBlockFactory,
    AssessmentFactory,
    ExternalToolViewBlockFactory,
    ExternalToolViewFactory,
    FileResourceBlockFactory,
    ForumTopicBlockFactory,
    HTMLContentBlockFactory,
    JupyterBlockFactory,
    SimpleInteractiveToolBlockFactory,
    SimpleInteractiveToolFactory,
    SurveyBlockFactory,
    VideoBlockFactory,
)
from kinesinlms.learning_library.models import Block, UnitBlock
from kinesinlms.sits.constants import SimpleInteractiveToolType

logger = logging.getLogger(__name__)

# BUILDER CLASSES
# Add custom logic to set up each block after creation.
# Creators should handle multiple steps for creating related
# blocks and any extra config


class BaseBlockBuilder:
    @abstractmethod
    def create_block(self, block_subtype: str = None) -> Block:
        pass

    def create_related_models(
        self, block_instance: Block, block_subtype: str = None
    ) -> Optional[List]:
        return None

    def create_unit_block(
        self, block_instance: Block, course_unit: CourseUnit
    ) -> UnitBlock:
        # Make sure we order this new unit_block as the last in the sequence
        next_order_index = course_unit.unit_blocks.count()
        unit_block = UnitBlock.objects.create(
            course_unit=course_unit, block=block_instance, block_order=next_order_index
        )
        return unit_block


class HTMLContentBlockBuilder(BaseBlockBuilder):
    def create_block(self, block_subtype: str = None) -> Block:
        block_instance = HTMLContentBlockFactory.create()
        return block_instance


class FileResourceBlockBuilder(BaseBlockBuilder):
    def create_block(self, block_subtype: str = None) -> Block:
        block_instance = FileResourceBlockFactory.create()
        return block_instance


class VideoBlockBuilder(BaseBlockBuilder):
    def create_block(self, block_subtype: str = None) -> Block:
        block_instance = VideoBlockFactory.create()
        return block_instance


class JupyterBlockBuilder(BaseBlockBuilder):
    def create_block(self, block_subtype: str = None) -> Block:
        block_instance = JupyterBlockFactory.create()
        return block_instance


class ExternalToolViewBlockBuilder(BaseBlockBuilder):
    def create_block(self, block_subtype: str = None) -> Block:
        block_instance = ExternalToolViewBlockFactory.create()
        external_tool_view = ExternalToolViewFactory.create(block=block_instance)
        logger.debug(
            f"Created initial external tool view {external_tool_view} "
            f"and block {block_instance}  "
        )
        return block_instance


class SimpleInteractiveToolBlockBuilder(BaseBlockBuilder):
    def create_block(self, block_subtype: str = None) -> Block:
        block_instance = SimpleInteractiveToolBlockFactory.create()
        return block_instance

    def create_related_models(
        self, block_instance: Block, block_subtype: str = None
    ) -> Optional[List]:
        created_instances = []

        # Makes sure this is a valid ASSESSMENT type.
        try:
            SimpleInteractiveToolType[block_subtype]
        except KeyError:
            raise Exception(f"Invalid SimpleInteractiveToolType type : {block_subtype}")

        sit_instance = SimpleInteractiveToolFactory.create(
            block=block_instance, tool_type=block_subtype
        )

        created_instances.append(sit_instance)

        return created_instances


class SurveyBlockBuilder(BaseBlockBuilder):
    def create_block(self, block_subtype: str = None) -> Block:
        block_instance = SurveyBlockFactory.create()
        return block_instance


class ForumTopicBlockBuilder(BaseBlockBuilder):
    """
    Create initial models for a forum topic.
    This will not involve any API calls to the forum service,
    this is only a local model setup. The course author or
    downstream admin logic will need to configure the FormTopic
    model instance for use with remote forum service, including
    setting up the remote objects, storing their IDs, etc.
    """

    def create_block(self, block_subtype: str = None) -> Block:
        block_instance = ForumTopicBlockFactory.create()
        logger.debug(f"Created initial FORUM_TOPIC block k {block_instance}")
        # Set up one ForumTopic instance for this block.
        forum_topic = ForumTopic.objects.create(block=block_instance)
        logger.debug(
            f"  - Created initial ForumTopic instance {forum_topic} "
            f"for block {block_instance}"
        )
        return block_instance


class AssessmentBlockBuilder(BaseBlockBuilder):
    def create_block(self, block_subtype: str = None) -> Block:
        block_instance = AssessmentBlockFactory.create()
        return block_instance

    def create_related_models(
        self, block_instance: Block, block_subtype: str = None
    ) -> Optional[List]:
        created_instances = []

        # Makes sure this is a valid ASSESSMENT type.
        try:
            AssessmentType[block_subtype]
        except KeyError:
            raise Exception(f"Invalid ASSESSMENT type : {block_subtype}")

        asssement_instance = AssessmentFactory.create(
            block=block_instance, type=block_subtype, graded=True
        )

        created_instances.append(asssement_instance)

        return created_instances


class BlockBuilderDirector:
    """
    This is a simple builder pattern that goes through a couple
    steps to create a block and its related models (depending
    on the context).
    """

    @classmethod
    def insert_existing_block(cls, block: Block, course_unit: CourseUnit) -> UnitBlock:
        """
        Insert an existing Block into a CourseUnit
        """

        builder = BlockBuilderDirector.get_builder(block_type=block.type)

        unit_block = builder.create_unit_block(
            block_instance=block, course_unit=course_unit
        )
        return unit_block

    @classmethod
    def build_block(
        cls,
        block_type: str,
        block_subtype: str = None,
        course_unit: CourseUnit = None,
        insert_index: int = None,
    ) -> Tuple[Block, UnitBlock]:
        """
        Create a new instance of the requested block type.
        If course_unit is defined, also create a UnitBlock instance,
        otherwise return None for course_unit.

        If course_unit IS provided, the user is creating this block
        as part of a course and wants a UnitBlock instance created and
        set to the correct position at the end of the blocks in the
        CourseUnit.

        If course_unit IS NOT provided, the caller is creating this block
        as part of a library in no relation to a course so no UnitBlock
        needs to be created.

        If insert_index is provided, add the block at that index, and move
        every other block down.
        """

        # Validate
        if course_unit.type != CourseUnitType.STANDARD.name:
            raise Exception(
                f"Cannot add blocks to a Course Unit of type : {course_unit.type}"
            )

        # Build BLOCK...
        builder = BlockBuilderDirector.get_builder(block_type=block_type)
        block_instance = builder.create_block()

        # Build related models...
        if block_subtype:
            builder.create_related_models(
                block_instance=block_instance, block_subtype=block_subtype
            )

        # Build unit block ...
        if course_unit:
            unit_block = builder.create_unit_block(
                block_instance=block_instance, course_unit=course_unit
            )
        else:
            unit_block = None

        # Insert the new block at the correct index and
        # move all other blocks down.

        if unit_block and insert_index is not None:
            for ub in course_unit.unit_blocks.filter(block_order__gte=insert_index):
                if ub != unit_block and ub.block_order >= insert_index:
                    ub.block_order += 1
                    ub.save()
            unit_block.block_order = insert_index
            unit_block.save()

        return block_instance, unit_block

    @classmethod
    def get_builder(cls, block_type: str) -> BaseBlockBuilder:
        if block_type == BlockType.HTML_CONTENT.name:
            return HTMLContentBlockBuilder()
        if block_type == BlockType.FILE_RESOURCE.name:
            return FileResourceBlockBuilder()
        elif block_type == BlockType.VIDEO.name:
            return VideoBlockBuilder()
        elif block_type == BlockType.ASSESSMENT.name:
            return AssessmentBlockBuilder()
        elif block_type == BlockType.FORUM_TOPIC.name:
            return ForumTopicBlockBuilder()
        elif block_type == BlockType.SURVEY.name:
            return SurveyBlockBuilder()
        elif block_type == BlockType.SIMPLE_INTERACTIVE_TOOL.name:
            return SimpleInteractiveToolBlockBuilder()
        elif block_type == BlockType.EXTERNAL_TOOL_VIEW.name:
            return ExternalToolViewBlockBuilder()
        elif block_type == BlockType.JUPYTER_NOTEBOOK.name:
            return JupyterBlockBuilder()
        else:
            raise NotImplementedError(
                f"Block factory cannot create blocks of type {block_type}"
            )
