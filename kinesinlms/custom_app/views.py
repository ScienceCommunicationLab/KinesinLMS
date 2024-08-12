import logging
from typing import List

from django.shortcuts import render

from kinesinlms.speakers.models import Speaker, CourseSpeaker

logger = logging.getLogger(__name__)


# These methods are called by a main view method in course/views.py
# They aren't meant to be called directly from an url (at least not yet).

def course_speakers(request, course, custom_app):
    assert course is not None
    assert custom_app is not None

    template = "custom_app/course_speakers.html"
    course_sps: List[Speaker] = CourseSpeaker.objects.filter(course=course).all()

    # If we have a custom image for this speaker use that
    # instead of the default image

    context = {
        "course": course,
        "course_speakers": course_sps,
        "custom_app_slug_active": custom_app.slug,
        "current_course_tab_name": "Course Speakers",
        "custom_app": custom_app,
    }

    return render(request, template, context)


def peer_review_journal(request, course, custom_app):
    assert course is not None
    assert custom_app is not None

    template = "custom_app/peer_review_journal.html"

    context = {
        "course": course,
        "custom_app_slug_active": custom_app.slug,
        "custom_app": custom_app,
    }

    return render(request, template, context)


def simple_html_content(request, course, custom_app):
    assert course is not None
    assert custom_app is not None

    template = "custom_app/simple_html_content.html"

    context = {
        "course": course,
        "custom_app_slug_active": custom_app.slug,
        "custom_app": custom_app
    }

    return render(request, template, context)
