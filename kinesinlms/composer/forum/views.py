from enum import Enum

from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render

from kinesinlms.course.models import Course
from kinesinlms.forum.models import CourseForumGroup, ForumSubcategoryType
from kinesinlms.forum.service.base_service import BaseForumService
from kinesinlms.forum.utils import get_forum_provider, get_forum_service


class ForumItemType(Enum):
    """
    Defines the basic objects in a remote forum we need to set up for a course
    in order to support FORUM_TOPIC type blocks.
    """
    COURSE_FORUM_CATEGORY = "Course category"
    COURSE_FORUM_GROUP = "Course group"
    DEFAULT_COHORT_FORUM_GROUP = "Default cohort group"
    DEFAULT_COHORT_FORUM_SUBCATEGORY = "Default cohort subcategory"


def create_forum_item_hx(request, course_id: int, forum_item_slug: str):
    """
    Create a forum item in the remote forum provider for the given course.
    This method handles the various forum types defined in the ForumItemType enum.

    Args:
        request: The HTTP request object.
        course_id: The ID of the course to create the forum item for.
        forum_item_slug: The slug of the forum item type to create.

    Returns:
        HttpResponse: The response object.
    """

    course = get_object_or_404(Course, id=course_id)

    if forum_item_slug not in [item.name for item in ForumItemType]:
        return HttpResponseBadRequest(f"'{forum_item_slug}' is not a forum item type.")

    forum_provider = get_forum_provider()
    forum_service: BaseForumService = get_forum_service()

    if not forum_provider:
        return HttpResponseBadRequest("No forum provider is configured.")

    context = {
        "forum_provider": forum_provider,
        "course": course,
        "error": None
    }
    template = f"composer/forum/forum_item_status/{forum_item_slug.lower()}_status.html"

    if forum_item_slug == ForumItemType.COURSE_FORUM_GROUP.name:

        forum_group, created = forum_service.get_or_create_course_forum_group(course=course)
        context["course_forum_group"] = forum_group
        context["course_forum_group_created"] = created

    elif forum_item_slug == ForumItemType.DEFAULT_COHORT_FORUM_GROUP.name:

        default_cohort = course.get_default_cohort()
        cohort_forum_group, created = forum_service.get_or_create_cohort_forum_group(cohort=default_cohort)
        context["cohort_forum_group"] = cohort_forum_group
        context["cohort_forum_group_created"] = created

    elif forum_item_slug == ForumItemType.COURSE_FORUM_CATEGORY.name:

        forum_category, created = forum_service.get_or_create_forum_category(course=course)
        context["course_forum_category"] = forum_category
        context["course_forum_created"] = created

    elif forum_item_slug == ForumItemType.DEFAULT_COHORT_FORUM_SUBCATEGORY.name:

        try:
            CourseForumGroup.objects.get(course=course)
        except CourseForumGroup.DoesNotExist:
            context["error"] = ("A forum course group must be created before "
                                "creating a cohort forum subcategory.")
            return render(request, template, context)

        default_cohort = course.get_default_cohort()
        if default_cohort.cohort_forum_group:
            cohort_forum_group = default_cohort.cohort_forum_group
        else:
            context["error"] = ("A default cohort forum group must be created before "
                                "creating a default cohort forum subcategory.")
            return render(request, template, context)

        forum_category, created = forum_service.get_or_create_forum_category(course=course)

        try:
            forum_subcategory, created = forum_service.get_or_create_forum_subcategory(
                forum_category=forum_category,
                subcategory_type=ForumSubcategoryType.COHORT.name,
                cohort_forum_group=cohort_forum_group)
            context["course_forum_subcategory"] = forum_subcategory
            context["course_forum_subcategory_created"] = created
        except Exception as e:
            context["error"] = f"Could not create forum subcategory : {e}"
            return render(request, template, context)
    else:
        context["error"] = f"'{forum_item_slug}' is not a valid forum item type."

    return render(request, template, context)
