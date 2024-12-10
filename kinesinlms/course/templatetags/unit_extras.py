import logging
from typing import Dict, List, Optional

from django import template
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.safestring import mark_safe

from kinesinlms.assessments.utils import get_answer_data
from kinesinlms.course.models import Bookmark, Course, CourseNode, CourseUnit
from kinesinlms.forum.models import ForumCategory, ForumSubcategory, ForumTopic
from kinesinlms.learning_library.constants import ResourceType
from kinesinlms.learning_library.models import (
    Block,
    BlockType,
    LearningObjective,
    Resource,
    UnitBlock,
)
from kinesinlms.learning_library.utils import get_learning_objectives
from kinesinlms.survey.models import SurveyCompletion
from kinesinlms.survey.service import SurveyEmailService

logger = logging.getLogger(__name__)

register = template.Library()

User = get_user_model()


# PARSING TEMPLATE KEYWORDS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# TODO: Might want to move this to separate module


def get_anon_user_id(user):
    return user.anon_username


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# FILTERS TAGS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@register.filter
def extrernal_video_badge(video_source_info: Dict):
    """
    Render a simple badge link to an external video resource.
    Expects a Dictionary like:
        {
            "source": "(YOUTUBE/VIMEO)"
            "video_id": "3159058FAVB"
        }
    """

    html_result = ""
    try:
        video_source = video_source_info["source"]
        video_id = video_source_info["video_id"]
        if video_source.upper() == "YOUTUBE":
            icon = '<i class="fab fa-youtube me-2"></i>'
            external_url = f"https://youtu.be/{video_id}"
        elif video_source.upper() == "VIMEO":
            icon = '<i class="fab fa-vimeo-v me-2"></i>'
            external_url = f"https://vimeo.com/{video_id}"
        else:
            raise Exception(f"external_video_badge: Unsupported video format : {video_source}")
        html_result = (
            f'<a class="btn btn-sm btn-info mt-2 me-2" '
            f'   href="{external_url}" target="_blank"  >'
            f"{icon} View on {video_source}"
            f"</a>"
        )
    except Exception:
        logger.exception(f"Could not render external_video_badge simple " f"tag for video_info: {video_source_info}")
    return html_result


@register.filter
def highlight_search(content, search_text):
    highlighted = content.replace(search_text, f'<span class="highlight">{search_text}</span>')
    return mark_safe(highlighted)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# SIMPLE TAGS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@register.simple_tag
def block_is_read_only(block: Block, course_unit: CourseUnit) -> bool:
    """
    In some cases we might *not* want to show instructions, such
    as when SITs are shown in read-only mode.
    """

    # After course finished, it's always read-only
    course = course_unit.course
    if course.has_finished:
        return True

    try:
        unit_block = UnitBlock.objects.get(block=block, course_unit=course_unit)
        # We don't show instructions when block is read-only
        return unit_block.read_only
    except Exception:
        return True


@register.simple_tag
def get_assessment_label(block: Block, course_unit: CourseUnit) -> str:
    """
    Get an assessment label. We allow the UnitBlock to have
    a label definition that overrides the Assessment model's label.

    Args:
        block:
        course_unit:

    Returns
        String to be used for assessment label.

    """
    label = ""
    try:
        unit_block = block.unit_blocks.get(course_unit=course_unit)
        if unit_block.label:
            label = unit_block.label
        elif block.assessment.label:
            label = block.assessment.label
        else:
            label = ""
    except Exception:
        logger.exception(f"Could not render label for ASSESSMENT-type " f"block {block} course_unit {course_unit} ")
    return label


@register.simple_tag
def get_html_content_label(block: Block, course_unit: CourseUnit) -> str:
    """
    Get an assessment label. There's an order we follow to determine what, if any,
    label to show for an assessment.

    Args:
        block:
        course_unit:

    Returns
        String to be used for assessment label.

    """
    label = "Course content..."
    try:
        unit_block = block.unit_blocks.get(course_unit=course_unit)
        if block.display_name and unit_block.label:
            label = f"{block.display_name} {unit_block.label}"
        elif unit_block.label:
            label = unit_block.label
        elif block.display_name:
            label = block.display_name
    except Exception:
        logger.exception(f"Could not render label for HTML_CONTENT-type " f"block {block} course_unit {course_unit} ")
    return label


@register.simple_tag
def get_survey_label(block: Block, course_unit: CourseUnit) -> str:
    label = None
    try:
        unit_block = block.unit_blocks.get(course_unit=course_unit)
        if block.display_name and unit_block.label:
            label += f"{block.display_name} {unit_block.label}"
        elif unit_block.label:
            label += unit_block.label
        elif block.display_name:
            label += block.display_name
    except Exception:
        logger.exception(f"Could not render label for SURVEY-type " f"block {block} course_unit {course_unit} ")
    if label is None:
        label = "Survey"

    return label


@register.simple_tag
def get_activity_label(block: Block, course_unit: CourseUnit) -> str:
    """
    Get an activity label. There's an order we follow to determine what, if any,
    label to show for an activity.

    Args:
        block:
        course_unit:

    Returns
        String to be used for assessment label.

    """
    try:
        unit_block = block.unit_blocks.get(course_unit=course_unit)
        if unit_block.label:
            return unit_block.label
    except Exception:
        logger.exception(f"Could not render label for activity-type " f"block {block} course_unit {course_unit} ")
    return ""


@register.simple_tag
def get_unit_blocks_for_answer_list(answer_list_block: Block) -> List[UnitBlock]:
    """
    Get a list of unit blocks as defined by the json_data in the provided ANSWER_LIST-type Block.

    Args:
        answer_list_block:

    Returns:
    List of UnitBlock instances.
    """
    try:
        unit_block_slugs = answer_list_block.json_content.get("unit_block_slugs")
        unit_blocks = UnitBlock.objects.filter(slug__in=unit_block_slugs).all()
        return unit_blocks
    except Exception:
        logger.exception("Could not render ANSWER_LIST type block")
        return []


@register.simple_tag
def get_assessment_readonly_data(unit_block: UnitBlock, user):
    """
    Get assessment read only data, using the assessment slug as a lookup.
    Provide the course too, as Assessment slugs are only unique in conjunction
    with a course.

    Args:
        unit_block:
        user:

    """
    assert unit_block is not None
    assert user is not None

    try:
        assessment = unit_block.block.assessment
        course = unit_block.course_unit.course
        data = get_answer_data(course, assessment, user)
        return data
    except Exception:
        logger.exception(
            f"get_assessment_readonly_data() Could not use unit_block {unit_block.slug} "
            f"to get data for unit_block: {unit_block}  user: {user}"
        )
        data = {}
    return data


@register.simple_tag
def get_assessment_readonly_answer_text(unit_block: UnitBlock, user):
    """
    Get assessment read only answer, using the assessment slug as a lookup.
    Provide the course too, as Assessment slugs are only unique in conjunction
    with a course.

    This tag is only slightly different from get_assessment_readonly_data in that
    in only returns the user's answer.
    """
    assert unit_block is not None
    assert user is not None

    answer_text = None
    try:
        assessment = unit_block.block.assessment
        course = unit_block.course_unit.course
        data = get_answer_data(course, assessment, user)
        answer_text = data["answer_text"]
    except Exception:
        logger.exception(
            f"get_assessment_readonly_data() Could not use unit_block {unit_block.slug} "
            f"to get data for unit_block: {unit_block}  user: {user}"
        )

    if not answer_text:
        answer_text = "( no answer )"

    return answer_text


@register.simple_tag
def send_survey_reminder_email_if_required(block: Block, course: Course, user):
    """
    Send a survey reminder email if required.
    """

    logger.debug(f"Sending survey reminder for course {course} block {block} user {user}")

    try:
        survey = block.survey_block.survey
    except Exception:
        logger.exception(f"Could not get survey for block {block}")
        return None

    if survey.send_reminder_email:
        # Schedule the survey email. This call will ignore the request
        # if the email is already scheduled.
        SurveyEmailService.schedule_survey_email(course_survey=survey, user=user)

    return ""


@register.simple_tag
def get_survey_info(block: Block, course: Course, user: User) -> Optional[Dict]:
    """
    Get information about a survey so that we can render it as an iframe, including
    (most importantly) the users anon info in that link.

    TODO:
        This was a very rudimentary way of handling surveys when we had just PRE_COURSE
        POST_COURSE and FOLLOW_UP. Starting in Aug 2022 we needed to handle variable
        number of surveys throughout the course. A temporary solution is to include
        provider's survey_id in the json_content for the block...but this needs a better approach.

    """

    if block.type != BlockType.SURVEY.name:
        logger.error("get_survey_info() passed a non-survey block")
        return None

    try:
        survey = block.survey_block.survey
    except Exception as e:
        logger.exception(f"Could not get survey for block {block} : {e}")
        return {}

    survey_type = survey.type
    survey_id = survey.id
    if not survey_type and not survey_id:
        return None

    if not survey:
        logger.warning(f"Cannot find survey type: {survey_type} for course {course}")
        return None

    survey_url_for_user = survey.url_for_user(user=user)

    # Check if user already completed survey
    try:
        survey_completion = SurveyCompletion.objects.get(survey=survey, user=user)
        completed_date = survey_completion.updated_at
    except SurveyCompletion.DoesNotExist:
        completed_date = None

    # TODO: configure height per survey if we need that functionality
    height = 2500

    survey_info = {
        "height": height,
        "survey_url": survey_url_for_user,
        "survey_name": survey.name,
        "completed_date": completed_date,
        "provider_type": survey.provider.type,
        "provider_name": survey.provider.name,
    }

    return survey_info


@register.simple_tag
def learning_objectives(course_unit: CourseUnit, unit_node: CourseNode) -> List[LearningObjective]:
    try:
        return get_learning_objectives(course_unit=course_unit, current_unit_node=unit_node)
    except Exception:
        logger.exception("Error using 'learning_objectives' tag")
    return []


@register.simple_tag
def can_view_course_admin(user, course) -> bool:
    can_view = course.can_view_course_admin(user)
    return can_view


@register.simple_tag
def can_view_course_admin_cohorts(user, course) -> bool:
    can_view = course.can_view_course_admin_cohorts(user)
    return can_view


@register.simple_tag
def can_view_course_admin_analytics(user, course) -> bool:
    can_view = course.can_view_course_admin_analytics(user)
    return can_view


@register.simple_tag
def can_view_course_admin_enrollment(user, course) -> bool:
    return course.can_view_course_admin_enrollment(user)


@register.simple_tag
def can_view_course_admin_assessments(user, course) -> bool:
    return course.can_view_course_admin_assessments(user)


@register.simple_tag
def can_view_course_admin_resources(user, course) -> bool:
    return course.can_view_course_admin_resources(user)


@register.simple_tag
def get_bookmark(user, course, unit_node_id) -> Optional[Bookmark]:
    try:
        bookmark = Bookmark.objects.get(student=user, course=course, unit_node_id=unit_node_id)
        return bookmark
    except Bookmark.DoesNotExist:
        return None


@register.simple_tag
def get_forum_topic_id(course, block, cohort) -> Optional[int]:
    """
    Given a user, course, block and cohort, return the topic_id for the
    corresponding ForumTopic.
    """

    if not cohort:
        cohort = course.get_default_cohort()

    if not course or not block or not cohort:
        logger.warning("get_forum_topic_id() tag: Cannot get forum topic id. Missing course, block or cohort.")
        return None
    try:
        forum_category = ForumCategory.objects.get(course=course)
        forum_subcategory = ForumSubcategory.objects.get(
            cohort_forum_group=cohort.cohort_forum_group, forum_category=forum_category
        )
        disc_topic = ForumTopic.objects.get(forum_subcategory=forum_subcategory, block=block)
        topic_id = disc_topic.topic_id
    except Exception:
        logger.exception(f"Could not load ForumTopic")
        topic_id = None
    return topic_id


@register.simple_tag(takes_context=True)
def image(context, uuid) -> Optional[str]:
    """
    Return the html and IMAGE resource.
    """
    return resource(context, uuid, limit_to_image=True)


@register.simple_tag(takes_context=True)
def image_url(context, uuid) -> Optional[str]:
    """
    Return the html and IMAGE resource.
    """
    return resource_url(context, uuid, limit_to_image=True)


@register.simple_tag(takes_context=True)
def resource(context, uuid, limit_to_image=False) -> Optional[str]:
    """
    Return the html for a resource.
    """

    block = context.get("block", None)
    if block is None:
        # We can't get the resource because we need to know
        # it's explicitly linked to this block.
        logger.warning(f"Could not load resource for uuid {uuid} because " f"block is not in context")
        return None

    try:
        resource: Resource = block.resources.get(uuid=uuid)
    except Resource.DoesNotExist:
        logger.warning(f"Could not find resource for block {block} " f"and uuid {uuid}")
        return ""

    if limit_to_image and resource.type != ResourceType.IMAGE.name:
        logger.warning("Cannot write HTML for resource. Not an image.")
        return ""

    try:
        html = resource.as_html
        return mark_safe(html)
    except Exception:
        logger.exception(f"Could not load resource for block {block} and uuid {uuid}")
        return ""


@register.simple_tag(takes_context=True)
def resource_url(context, uuid, limit_to_image=False) -> Optional[str]:
    """
    Return the url for a resource.
    """

    block = context.get("block", None)
    if block is None:
        # We can't get the resource because we need to know
        # it's explicitly linked to this block.
        logger.warning(f"Could not load resource for uuid {uuid} because " f"block is not in context")
        return None

    try:
        resource: Resource = block.resources.get(uuid=uuid)
    except Resource.DoesNotExist:
        logger.warning(f"Could not find resource for block {block} " f"and uuid {uuid}")
        return ""

    if limit_to_image and resource.type != ResourceType.IMAGE.name:
        logger.warning("Cannot write HTML for resource. Not an image.")
        return ""

    try:
        return resource.url
    except Exception:
        logger.exception(f"Could not load resource for block {block} and uuid {uuid}")
        return ""


@register.simple_tag(takes_context=True)
def anon_user_id(context) -> str:
    if context.user and context.user.is_authenticated:
        return context.user.anon_username
    else:
        return ""


@register.simple_tag(takes_context=True)
def username(context) -> str:
    if context.user and context.user.is_authenticated:
        return context.user.username
    else:
        return ""


@register.simple_tag(takes_context=True)
def module_link(context, module_content_index: int) -> str:
    return unit_link(context, module_content_index, 1, 1)


@register.simple_tag(takes_context=True)
def section_link(context, module_content_index: int, section_content_index: int) -> str:
    return unit_link(context, module_content_index, section_content_index, 1)


@register.simple_tag(takes_context=True)
def unit_link(
    context,
    module_content_index: int,
    section_content_index: int,
    unit_content_index: int,
) -> str:
    current_course = context.get("course", None)
    if current_course is None:
        return ""
    module: CourseNode = current_course.course_root_node.children.get(content_index=module_content_index)
    section: CourseNode = module.children.get(content_index=section_content_index)
    unit: CourseNode = section.children.get(content_index=unit_content_index)
    unit_url = reverse(
        "course:unit_page",
        kwargs={
            "course_slug": current_course.slug,
            "course_run": current_course.run,
            "module_slug": module.slug,
            "section_slug": section.slug,
            "unit_slug": unit.slug,
        },
    )
    link = f"<a href='{unit_url}'>Unit {module_content_index}.{section_content_index}.{unit_content_index}</a>"
    return mark_safe(link)


@register.simple_tag(takes_context=True)
def unit_slug_link(context, unit_slug: str) -> str:
    """
    Builds a link to a CourseUnit given a CourseUnit slug.
    """
    current_course = context.get("course", None)
    if current_course is None:
        return ""
    try:
        unit_nodes = current_course.course_root_node.get_leafnodes().filter(slug=unit_slug)
        unit_node: CourseNode = unit_nodes.first()
    except Exception:
        logger.exception("Could not substitute UNIT_SLUG_LINK marker in template")
        return ""

    try:
        section_node = unit_node.parent
        module_node = section_node.parent
        unit_url = reverse(
            "course:unit_page",
            kwargs={
                "course_slug": current_course.slug,
                "course_run": current_course.run,
                "module_slug": module_node.slug,
                "section_slug": section_node.slug,
                "unit_slug": unit_node.slug,
            },
        )
        link = f"<a href='{unit_url}'>{unit_node.display_name}</a>"
        return mark_safe(link)
    except Exception:
        logger.exception(f"Could not build link to unit_node: {unit_node}")
        return ""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# INCLUSION TAGS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@register.inclusion_tag("course/custom/block_links.html")
def block_links(block_id: int, course_id: int) -> Dict:
    """
    Displays a list of links to the CourseUnits this block
    appears in for a particular course.

    Args:
        block_id:
        course_id:

    Returns:
    A dictionary with one 'block_links' property containing
    a list of block links.
    """

    collected_block_links = []
    block = Block.objects.get(id=block_id)
    course = Course.objects.get(id=course_id)
    course_units: List[CourseUnit] = block.units.filter(course=course)
    for course_unit in course_units:
        block_link = {
            "display_name": course_unit.display_name,
            "url": course_unit.get_url(course),
        }
        collected_block_links.append(block_link)

    result = {"block_links": collected_block_links}

    return result
