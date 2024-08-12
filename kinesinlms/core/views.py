# Create your views here.
# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from kinesinlms.course.models import CourseUnit, Enrollment
from kinesinlms.course.models import CourseResource
from kinesinlms.learning_library.models import Resource


def can_view_course_resource(course_resource: CourseResource, user):
    """
    Returns a boolean indicating whether a user can view
    this CourseResource or not.
    """
    if user.is_superuser or user.is_staff:
        return True
    enrollment_exists = Enrollment.objects.filter(
        student=user,
        course=course_resource.course,
        active=True,
    ).exists()
    return enrollment_exists


def can_view_resource(resource: Resource, user) -> bool:
    """
    Returns a boolean indicating whether a user can view this Resource.
    """
    if user.is_superuser or user.is_staff:
        return True

    # Check if the user is enrolled in any course that includes this resource
    enrollment_exists = Enrollment.objects.filter(
        student=user,
        course__in=CourseUnit.objects.filter(
            contents__block_resources__resource=resource
        ).values_list("course", flat=True),
        active=True,
    ).exists()

    return enrollment_exists
