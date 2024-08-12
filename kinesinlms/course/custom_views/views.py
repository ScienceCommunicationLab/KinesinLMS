import logging
from typing import List, Dict

from kinesinlms.course.models import Course, CourseUnit
from kinesinlms.course.constants import CourseUnitType
from kinesinlms.learning_library.models import BlockType, UnitBlock

logger = logging.getLogger(__name__)

"""

    These are custom views for a course. They render units that have layout and/or functionality
    are specific to the course (and not available from a generic template for nodes).
    These views and templates therefore have knowledge of the particulars
    of a specific course unit and its data.

"""


class NoCustomTemplateDefined(Exception):
    pass


class NoCustomContextDefined(Exception):
    pass


def get_custom_unit_template(course: Course, course_unit: CourseUnit) -> str:
    """
    Return the subdirectory path to a custom template, if defined
    :param course:
    :param course_unit:
    :return:
    """
    assert course_unit is not None

    if course_unit.type == CourseUnitType.MY_RESPONSES.name:
        return "course/custom/my_responses.html"
    elif course_unit.type == CourseUnitType.PRINTABLE_REVIEW.name:
        return "course/custom/printable_review.html"
    else:
        raise NoCustomTemplateDefined(f"No course_unit type : {course_unit.type}")


def get_custom_unit_data(request, course: Course, course_unit: CourseUnit) -> Dict:
    """
    Provides custom data for the unit context. Use the unit type and
    the definition in the unit.json_content, along with any necessary db queries,
    to build up the return a custom_data object containing data needed for this
    custom view.

    Right now we only have two kinds of custom views:
        - One for MRP and MEP 'edit' pages where a student can edit any of the questions in
        the MRP or MEP
        - One for MRP and MEP 'print' pages

    """
    assert course is not None
    assert course_unit is not None
    student = request.user
    if course_unit.type == CourseUnitType.MY_RESPONSES.name:
        custom_data = get_my_responses_data(student=student, course=course, course_unit=course_unit)
    elif course_unit.type == CourseUnitType.PRINTABLE_REVIEW.name:
        """
            The reason we can't just use get_my_responses_data for this
            custom type is that the My Responses page relies on React component
            to load current answers. But in the print case, we have to get the
            answers loaded up before rendering the template. So we have a diff method
            for that case.
        """
        custom_data = get_printable_review_data(student=student, course=course, course_unit=course_unit)
    else:
        # Don't need to raise an error. There might be custom views that don't have custom data
        return {}
    return custom_data


def get_printable_review_data(student, course: Course, course_unit: CourseUnit) -> Dict:
    """
    Get data for a 'Printable Review' page.

    :param student:
    :param course:
    :param course_unit:

    :return:
    A dictionary of 'custom data' that specific certain properties and data
    the Printable Review template wants.

    """
    assert student is not None
    assert course is not None
    assert course_unit is not None

    # For printable review, all we have to do is pass back the data stored in json_content
    custom_data = course_unit.json_content
    if custom_data:
        # Sanity checks
        groups = custom_data.get('groups', None)
        for group_json in groups:
            unit_block_slugs = group_json.get('unit_block_slugs', [])
            if unit_block_slugs:
                unit_blocks = UnitBlock.objects.filter(slug__in=unit_block_slugs).all()
                # Order by how slugs are defined in custom component
                # Dang this is ugly, huh? Probably a better way.
                lookup = {unit_block.slug: unit_block for unit_block in unit_blocks}
                unit_blocks_sorted = []
                for unit_block_slug in unit_block_slugs:
                    unit_blocks_sorted.append(lookup[unit_block_slug])
                group_json['unit_blocks'] = unit_blocks_sorted
        if not groups:
            raise Exception("Printable Review json_content missing groups definition")
    else:
        assessment_blocks = get_unit_blocks_in_course(course=course, block_type=BlockType.ASSESSMENT)
        custom_data = {
            "groups": [
                {
                    "unit_blocks": assessment_blocks
                }
            ]
        }

    return custom_data


def get_my_responses_data(student, course: Course, course_unit: CourseUnit) -> dict:
    """
    Get custom data for a "My Responses"-type Unit.

    Args:
        student:
        course:
        course_unit:

    Returns:

        custom_data in the shape:

        {
            "groups": [
                {
                    "unit_block_slugs": [unit_block.slug for unit_block in unit_blocks],
                    "unit_blocks": unit_blocks
                }
                ... arbitrary number of groups
            ]
        }

    """

    custom_data = course_unit.json_content

    if custom_data:
        # Sanity checks
        groups = custom_data.get('groups', None)
        if not groups:
            raise Exception("My Responses View Review json_content missing groups definition")
        for group_json in groups:
            unit_block_slugs = group_json.get('unit_block_slugs', None)
            if unit_block_slugs:
                unit_blocks = list(map(lambda slug: UnitBlock.objects.get(slug=slug), unit_block_slugs))
                group_json['unit_blocks'] = unit_blocks
    else:
        # If not groups defined, return all UnitBlocks that have an Assessment Block.
        unit_blocks = get_unit_blocks_in_course(course=course, block_type=BlockType.ASSESSMENT)
        custom_data = {
            "groups": [
                {
                    "unit_block_slugs": [unit_block.slug for unit_block in unit_blocks],
                    "unit_blocks": unit_blocks
                }
            ]
        }

    return custom_data


def get_unit_blocks_in_course(course: Course, block_type: BlockType, limit_to_slugs: List = None) -> List[UnitBlock]:
    # TODO: Optimize! Probably better way of using join table
    # TODO: to get our list of slugs for assessments.
    course_units = CourseUnit.objects.filter(course=course)
    unit_blocks = UnitBlock.objects.filter(course_units__in=course_units).all()
    assessment_blocks = []
    for unit_block in unit_blocks:
        if unit_block.block.type == block_type.name:
            if limit_to_slugs and unit_block.slug not in limit_to_slugs:
                continue
            else:
                assessment_blocks.append(unit_block)

    return assessment_blocks
