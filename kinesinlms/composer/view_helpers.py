import logging
from typing import List

from django.urls import reverse

from kinesinlms.course.models import Course
from kinesinlms.email_automation.utils import get_email_automation_provider

logger = logging.getLogger(__name__)


def get_course_edit_tabs(current_course: Course, active_section) -> List:
    settings_url = None
    catalog_url = None
    content_url = None
    milestones_url = None
    badge_classes_url = None
    email_automations_url = None
    course_forum_url = None
    course_surveys_url = None

    if current_course:
        settings_url = reverse(
            "composer:course_edit_settings", kwargs={"pk": current_course.id}
        )
        catalog_url = reverse(
            "composer:course_catalog_description_edit",
            kwargs={
                "course_id": current_course.id,
                "pk": current_course.catalog_description.id,
            },
        )
        milestones_url = reverse(
            "composer:course_milestones_list", kwargs={"course_id": current_course.id}
        )
        badge_classes_url = reverse(
            "composer:course_badge_classes_list",
            kwargs={"course_id": current_course.id},
        )
        content_url = reverse(
            "composer:course_edit", kwargs={"course_id": current_course.id}
        )
        course_forum_url = reverse(
            "composer:course_forum_edit", kwargs={"course_id": current_course.id}
        )

        course_surveys_url = reverse(
            "composer:course_surveys_list", kwargs={"course_id": current_course.id}
        )

        resources_url = reverse(
            "composer:resources_list", kwargs={"course_id": current_course.id}
        )

        email_automation_provider = get_email_automation_provider()
        if email_automation_provider and email_automation_provider.enabled:
            email_automations_url = reverse(
                "composer:course_email_automations_settings_edit",
                kwargs={"pk": current_course.id},
            )

    course_settings_enabled = True

    section_tabs = [
        {
            "name": "Course Settings",
            "url": settings_url,
            "active": active_section == "course_settings",
            "enabled": course_settings_enabled,
        },
        {
            "name": "Catalog Info",
            "url": catalog_url,
            "active": active_section == "catalog",
            "enabled": current_course is not None,
        },
        {
            "name": "Contents",
            "url": content_url,
            "active": active_section == "content",
            "enabled": current_course is not None,
        },
        {
            "name": "Milestones",
            "url": milestones_url,
            "active": active_section == "milestones",
            "enabled": current_course is not None,
        },
        {
            "name": "Badges",
            "url": badge_classes_url,
            "active": active_section == "badges",
            "enabled": current_course is not None,
        },
        {
            "name": "Forum",
            "url": course_forum_url,
            "active": active_section == "course_forum",
            "enabled": current_course is not None,
        },
        {
            "name": "Surveys",
            "url": course_surveys_url,
            "active": active_section == "course_surveys",
            "enabled": current_course is not None,
        },
        {
            "name": "Resources",
            "url": resources_url,
            "active": active_section == "resources",
            "enabled": current_course is not None,
        },
    ]

    if email_automations_url:
        section_tabs.append(
            {
                "name": "Email Automations",
                "url": email_automations_url,
                "active": active_section == "email_automations",
                "enabled": current_course is not None,
            }
        )

    return section_tabs
