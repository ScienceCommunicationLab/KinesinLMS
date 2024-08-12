import logging

from django import template
from django.contrib.auth import get_user_model
from django.utils.safestring import mark_safe

from kinesinlms.tracking.event_types import TrackingEventType

logger = logging.getLogger(__name__)

register = template.Library()

User = get_user_model()


@register.simple_tag
def event_icon(event_type):
    """
    Return an appropriate icon for each supported event type.
    """

    # Show this icon if we don't have a specific one
    # for the incoming event_type
    default_icon_map = {
        "icon_holder_class": "default-icon",
        "icon_class": "bi bi-record-circle",
    }

    icon_map = {
        TrackingEventType.ENROLLMENT_ACTIVATED.name: {
            "icon_holder_class": "enrollment-icon",
            "icon_class": "bi bi-person-fill-add",
        },
        TrackingEventType.COURSE_VIDEO_ACTIVITY.name: {
            "icon_holder_class": "video-icon",
            "icon_class": "bi bi-youtube",
        },
        TrackingEventType.COURSE_PAGE_VIEW.name: {
            "icon_holder_class": "page-view-icon",
            "icon_class": "bi bi-file-earmark-richtext",
        },
        TrackingEventType.COURSE_ASSESSMENT_ANSWER_SUBMITTED.name: {
            "icon_holder_class": "assessment-icon",
            "icon_class": "bi bi-pencil-square",
        },
        TrackingEventType.COURSE_CUSTOM_APP_PAGE_VIEW.name: {
            "icon_holder_class": "custom-page-icon",
            "icon_class": "bi bi-file-medical",
        },
        TrackingEventType.FORUM_POST.name: {
            "icon_holder_class": "forum-icon",
            "icon_class": "bi bi-chat-left-dots",
        },
        TrackingEventType.BOOKMARK_CREATED.name: {
            "icon_holder_class": "bookmark-icon",
            "icon_class": "bi bi-bookmark-plus",
        },
        TrackingEventType.COURSE_SEARCH_REQUEST.name: {
            "icon_holder_class": "search-icon",
            "icon_class": "fas fa-search",
        },
        TrackingEventType.COURSE_BOOKMARKS_VIEW.name: {
            "icon_holder_class": "custom-page-icon",
            "icon_class": "bi bi-journal-bookmark",
        },
    }
    icon_info = icon_map.get(event_type, default_icon_map)
    icon_holder_class = icon_info["icon_holder_class"]
    icon_class = icon_info["icon_class"]
    icon_html = f'<div class="icon-holder {icon_holder_class} ml-2"><i class="{icon_class}"></i></div>'

    return mark_safe(icon_html)


@register.simple_tag
def event_display_name(event):
    event_names_map = {
        TrackingEventType.COURSE_PAGE_VIEW.name: "Unit page view",
        TrackingEventType.ENROLLMENT_ACTIVATED.name: "Enrolled in course",
        TrackingEventType.COURSE_ASSESSMENT_ANSWER_SUBMITTED.name: "Assessment submission",
        TrackingEventType.COURSE_HOME_VIEW.name: "Course home page view",
        TrackingEventType.COURSE_CUSTOM_APP_PAGE_VIEW.name: "Custom page view",
        TrackingEventType.FORUM_POST.name: "Forum post",
        TrackingEventType.COURSE_SEARCH_REQUEST.name: "Search",
        TrackingEventType.BOOKMARK_CREATED.name: "Created bookmark",
        TrackingEventType.COURSE_BOOKMARKS_VIEW.name: "Viewed bookmark page",
        TrackingEventType.COURSE_RESOURCE_DOWNLOAD.name: "Downloaded resource",
        TrackingEventType.COURSE_BLOCK_RESOURCE_DOWNLOAD.name: "Downloaded block resource",
    }

    if event.event_type == TrackingEventType.COURSE_VIDEO_ACTIVITY.name:
        try:
            name = event.event_data["video_event_type"].split(".")[-1].upper()
        except KeyError:
            logger.error(f"Missing video_event_type in event_data for event {event}")
            name = "Video activity"
    else:
        name = event_names_map.get(event.event_type, event.event_type)
    return name
