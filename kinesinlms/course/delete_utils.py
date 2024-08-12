import logging

from typing import List
from django.contrib.auth.models import Group

from kinesinlms.course.models import CourseUnit, MilestoneProgress
from kinesinlms.learning_library.models import BlockType, Block, Resource, UnitBlock

logger = logging.getLogger(__name__)


def delete_course(
    course: "kinesinlms.course.models.Course",
    delete_all_progress: bool = False,
    delete_exclusive_block_resources: bool = False,
) -> List[str]:
    """
    Delete a course and related models.

    Args:
        course:                             A course instance to delete
        delete_all_progress:                Delete all student progress for this course
        delete_exclusive_block_resources:   Delete Resources used by BlockResources if they're only used by this course

    Returns:
        List[str]:                          A list of warnings or errors that occurred during deletion
    """

    warnings = []

    if not course:
        raise ValueError("Course instance is required")

    if delete_all_progress:
        MilestoneProgress.objects.filter(course=course).delete()

    if delete_exclusive_block_resources:
        exclusive_resources = get_exclusive_resources(course)
        delete_resource_ids = [resource.id for resource in exclusive_resources]
    else:
        delete_resource_ids = []

    root_node = course.course_root_node
    for module_node in root_node.children.all():
        for section_node in module_node.children.all():
            for unit_node in section_node.children.all():
                try:
                    unit_block = getattr(unit_node, "unit")
                except CourseUnit.DoesNotExist:
                    unit_block = None
                if unit_block:
                    for child_block in unit_block.contents.all():
                        # Delete learning objectives if they're not used by
                        # any other courses...
                        for learning_objective in child_block.learning_objectives.all():
                            if learning_objective.blocks.count() == 1:
                                learning_objective.delete()

                        if child_block.type == BlockType.ASSESSMENT.name:
                            try:
                                child_block.assessment.delete()
                            except Exception:
                                logger.error(
                                    f"Could not delete assessment for block : {child_block}"
                                )
                        child_block.delete()
                    unit_block.delete()
    root_node.delete()

    # Delete course group
    groups = Group.objects.filter(name=course.course_group_name).all()
    for group in groups:
        logger.info(f"Deleting group: {group}")
        group.delete()

    # Delete catalog
    course.catalog_description.delete()

    # Delete course
    course.delete()

    # Course delete was ok, now delete exclusive resources
    # If a delete fails here, s'okay keep going and just report error to user.
    if delete_exclusive_block_resources and delete_resource_ids:
        try:
            Resource.objects.filter(id__in=delete_resource_ids).all().delete()
        except Exception as e:
            logger.warning(f"  - Could not delete exclusive resources : {e}")
            warnings.append("Could not delete some resources")

    return warnings


def get_exclusive_resources(course) -> list["kinesinlms.learning_library.models.Resource"]:
    """
    Get all block resources used by this course and no other.
    """
    course_units = CourseUnit.objects.filter(course=course)
    course_unit_blocks = UnitBlock.objects.filter(course_unit__in=course_units)
    blocks = Block.objects.filter(unit_blocks__in=course_unit_blocks)
    exclusive_resources = (
        Resource.objects.filter(block_resources__block__in=blocks)
        .prefetch_related("block_resources__block")
        .distinct()
    )
    return exclusive_resources
