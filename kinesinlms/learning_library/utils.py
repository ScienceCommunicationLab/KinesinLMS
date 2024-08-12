import logging
from typing import List

from django.contrib.auth import get_user_model

from kinesinlms.course.constants import CourseUnitType
from kinesinlms.learning_library.models import LearningObjective

logger = logging.getLogger(__name__)

User = get_user_model()


def get_learning_objectives_for_course(course):
    root_node = course.course_root_node
    block_ids = set()
    for module_node in root_node.children.all():
        for section_node in module_node.children.all():
            for unit_node in section_node.children.all():
                block_ids.update(unit_node.unit.contents.values_list('id', flat=True))

    if not block_ids:
        return None

    learning_objectives = get_learning_objectives_for_block_ids(block_ids)
    return learning_objectives


def get_learning_objectives(course_unit,
                            current_unit_node) -> List[LearningObjective]:
    # Collect the IDs of all Blocks contained in CourseUnits contained in the current CourseNode.
    block_ids = set()
    if course_unit.type == CourseUnitType.MODULE_LEARNING_OBJECTIVES.name:
        module_node = current_unit_node.parent.parent
        for section_node in module_node.children.all():
            for unit_node in section_node.children.all():
                block_ids.update(unit_node.unit.contents.values_list('id', flat=True))
    elif course_unit.type == CourseUnitType.SECTION_LEARNING_OBJECTIVES.name:
        section_node = current_unit_node.parent
        for unit_node in section_node.children.all():
            block_ids.update(unit_node.unit.contents.values_list('id', flat=True))
    else:
        block_ids.update(course_unit.contents.values_list('id', flat=True))

    learning_objectives = get_learning_objectives_for_block_ids(block_ids)

    return learning_objectives


def get_learning_objectives_for_block_ids(block_ids: set[int]) -> List[LearningObjective]:
    """
    Look up LearningObjects for a set of blocks. Order by slug.
    """
    if not block_ids:
        return []

    def sort_los(ele):
        slug = ele.slug
        try:
            ele = int(slug)
            return 0, ele, ''
        except ValueError:
            return 1, slug, ''

    block_ids = list(block_ids)
    learning_objectives = LearningObjective.objects.filter(blocks__id__in=block_ids).all().distinct()
    # Differential sort : slugs might be "1" or "Blah"

    learning_objectives = sorted(learning_objectives, key=sort_los)

    return learning_objectives
