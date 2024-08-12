# Utility functions for management-type tasks.
import logging
from typing import Dict

from waffle.models import Switch
from django.core.cache import cache
from kinesinlms.core.constants import SiteFeatures


from kinesinlms.catalog.models import CourseCatalogDescription
from kinesinlms.course.constants import NodeType
from kinesinlms.course.models import Course, CourseNode, CourseUnit, EnrollmentSurvey, EnrollmentSurveyQuestion
from kinesinlms.learning_library.models import UnitBlock

logger = logging.getLogger(__name__)


def delete_course_nav_cache(course_slug: str, course_run: str) -> bool:
    """
    Remove the course nav if saved in the cache.

    Args:
        course_slug:        Slug for course
        course_run:         Run for course

    Returns:
        name of cache variable.

    """
    course_nav_cache_name = f"{course_slug}_{course_run}_nav"
    deleted = cache.delete(course_nav_cache_name)
    return deleted


def duplicate_course(course: Course,
                     new_slug: str,
                     new_run: str,
                     duplicate_blocks: bool = False,
                     new_course_display_name: str = None,
                     new_course_short_name: str = None) -> Course:
    """
    Duplicate a course. This means duplicating top-level things like the Course
    and CatalogDescription, as well as navigation, but *not* blocks.

    We only duplicate blocks if the duplicate_blocks param is True,
    in which case we also need to duplicate any objects directly related to the block.
    (e.g. SimpleInteractiveTool).

    If duplicate_blocks is False, we link directly to existing blocks.

    Args:
        course:                     Instance of course to be duplicated
        new_slug:
        new_run:
        duplicate_blocks:           Boolean indicating whether we should also duplicate content blocks
                                    (Not implemented yet.)
        new_course_display_name:
        new_course_short_name:

    Returns:
        Instance of new course.

    """
    logger.info(f"Duplicating course : {course}")

    if not new_slug:
        new_slug = f"{course.slug}_COPY"
    if not new_run:
        new_run = f"{course.run}_COPY"

    if duplicate_blocks:
        raise ValueError("Not implemented.")

    # Dup catalog
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    new_course_catalog_description = duplicate_course_catalog_description(course.catalog_description)
    logger.info(f"  - new duplicated catalog description: {new_course_catalog_description}")

    # Dup enrollment surveys
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    if hasattr(course, "enrollment_survey"):
        new_enrollment_survey = duplicate_course_enrollment_survey(enrollment_survey=course.enrollment_survey)
        new_enrollment_survey.course = course
        new_enrollment_survey.save()

    # Dup course
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Need to create the new course before duplicating the nav
    # because the new CourseUnit objects will want a ref to the new course.
    skip_fields = [
        'run',
        'catalog_description'
        'course_root_node',
        'created_at',
        'updated_at',
        'start_date',
        'end_date',
        'advertised_start_date',
        'enrollment_start_date',
        'enrollment_end_date',
        'display_name',
        'short_name'
    ]
    new_course_kwargs = create_duplicate_kwargs(course, skip_fields=skip_fields)
    if not new_course_display_name:
        new_course_display_name = course.display_name + " COPY"
    if not new_course_short_name:
        new_course_short_name = course.short_name + " COPY"
    # Create a new root node so that we have it when creating the course. (We'll populate it further below...)
    new_course_root_node = CourseNode.objects.create(type=NodeType.ROOT.name)
    new_course = Course.objects.create(**new_course_kwargs,
                                       slug=new_slug,
                                       run=new_run,
                                       display_name=new_course_display_name,
                                       short_name=new_course_short_name,
                                       course_root_node=new_course_root_node,
                                       catalog_description=new_course_catalog_description)
    logger.info(f"  - new duplicated course : {new_course}")

    # Dup navigation (CourseNodes) and content (CourseUnit and potentially Blocks)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    node_copy_fields = [
        'type',
        'purpose',
        'display_name',
        'slug',
        'release_datetime',
        'content_index',
        'display_sequence'
    ]
    # I would have made this recursive, but I didn't trust myself.
    for module_node in course.course_root_node.children.all():
        new_model_node_kwargs = create_duplicate_kwargs(module_node, only_copy_fields=node_copy_fields)
        new_module_node = CourseNode.objects.create(parent=new_course_root_node, **new_model_node_kwargs)
        for section_node in module_node.children.all():
            new_section_node_kwargs = create_duplicate_kwargs(section_node, only_copy_fields=node_copy_fields)
            new_section_node = CourseNode.objects.create(parent=new_module_node, **new_section_node_kwargs)
            for unit_node in section_node.children.all():
                new_unit_node_kwargs = create_duplicate_kwargs(unit_node, only_copy_fields=node_copy_fields)
                new_unit_node = CourseNode.objects.create(parent=new_section_node, **new_unit_node_kwargs)
                # Copy the CourseUnit attached to the Unit CourseNode.
                new_course_unit = duplicate_course_unit(unit_node.unit, new_course=course)
                new_unit_node.unit = new_course_unit
                new_unit_node.save()
            new_section_node.save()
        new_module_node.save()
    new_course_root_node.save()
    logger.info(f"  - duplicated course nav")

    # Add child dups to new course
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    new_course.course_root_node = new_course_root_node
    new_course.save()
    logger.info(f"  - duplicated course")

    return new_course


def duplicate_course_enrollment_survey(enrollment_survey: EnrollmentSurvey) -> EnrollmentSurvey:
    """
    Duplicate an EnrollmentSurvey attached to the original course.
    """
    new_enrollment_survey = EnrollmentSurvey.objects.create()
    for question in enrollment_survey.questions.all():
        new_question = EnrollmentSurveyQuestion.objects.create(
            question_type=question.question_type,
            definition=question.definition,
            display_order=question.display_order
        )
        new_enrollment_survey.questions.add(new_question)
    return new_enrollment_survey


def duplicate_course_catalog_description(
        course_catalog_description: CourseCatalogDescription) -> CourseCatalogDescription:
    """
    Duplicate a course catalog description.
    Note that the new description will use the same values and
    assets as the original (which should probably be updated later), including:
    - custom_stylesheet
    - syllabus_url
    - trailer_video_url
    - thumbnail

    We always duplicate with visible=False, so that the user has time to edit and
    update the course before releasing.

    """
    skip_fields = [
        'visible'
    ]
    dup_catalog_kwargs = create_duplicate_kwargs(course_catalog_description, skip_fields=skip_fields)
    new_catalog_description = CourseCatalogDescription.objects.create(**dup_catalog_kwargs, visible=False)
    return new_catalog_description


def duplicate_course_unit(course_unit: CourseUnit,
                          new_course: Course,
                          duplicate_blocks: bool = False) -> CourseUnit:
    if duplicate_blocks:
        raise ValueError("Not implemented")

    only_copy_fields = [
        'slug',
        'type',
        'display_name',
        'short_description',
        'course_only',
        'html_content',
        'has_keywords',
        'json_content',
        'status'
    ]

    # Dup course unit
    course_unit_kwargs = create_duplicate_kwargs(course_unit, only_copy_fields=only_copy_fields)
    new_course_unit = CourseUnit.objects.create(**course_unit_kwargs)
    new_course_unit.course = new_course
    new_course_unit.save()

    # Dup all contents in course unit.
    for unit_block in course_unit.unit_blocks.all():
        # Note we don't yet handle duplicate_blocks=True here....
        only_copy_fields = [
            'block',
            'slug',
            'run',
            'label',
            'index_label',
            'block_order',
            'hide',
            'read_only',
            'include_in_summary'
        ]
        new_unit_block_kwargs = create_duplicate_kwargs(unit_block, only_copy_fields=only_copy_fields)
        UnitBlock.objects.create(course_unit=new_course_unit, **new_unit_block_kwargs)

    return new_course_unit


def create_duplicate_kwargs(model, only_copy_fields=None, skip_fields=None) -> Dict:
    """
    Build a kwargs list of field names we want to copy from the Course model.
    """
    always_skip_fields = [
        "id",
        "slug",
        "run",
        "course_root_node",
        "catalog_description"
    ]

    new_model_kwargs = {}
    fields = model._meta.fields
    for field in fields:
        if field.name in always_skip_fields:
            continue
        if skip_fields and field.name in skip_fields:
            continue
        elif only_copy_fields and field.name not in only_copy_fields:
            continue
        new_model_kwargs[field.name] = getattr(model, field.name)
    return new_model_kwargs


def setup_waffle() -> None:
    """
    Set up the initial waffle switches and flags.
    """
    logger.info("Turning on toggleable features:")
    logger.info("(These features can be managed via the 'management' tab, Django admin, or the command line.)")
    # Set up the default waffle switches
    for item in SiteFeatures:
        feature = Switch.objects.get_or_create(name=item.name)[0]
        feature.active = True
        feature.save()
        logger.info(f" - setting feature {item.name} to True")


