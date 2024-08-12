# Create your views here.
import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from kinesinlms.certificates.models import Certificate
from kinesinlms.badges.models import BadgeAssertion, BadgeClass, BadgeClassType
from kinesinlms.course.models import Enrollment, CoursePassed
from kinesinlms.course.utils_access import can_access_course

logger = logging.getLogger(__name__)


# noinspection PyUnresolvedReferences
@login_required
def index(request):
    enrollments = Enrollment.objects.filter(student=request.user, active=True)

    # Hold information about each course we'll show on dashboard
    courses_info = []

    student_has_badges = False
    user_badges_enabled = request.user.get_settings().enable_badges

    # Attach student progress info
    # For now we just care about whether student passed or not.
    for enrollment in enrollments:
        certificate = None
        try:
            passed_course = CoursePassed.objects.get(student=request.user,
                                                     course=enrollment.course)
        except CoursePassed.DoesNotExist:
            passed_course = False

        # Attach certificate information...
        if passed_course:
            if enrollment.course.enable_certificates:
                try:
                    certificate = Certificate.objects.get(student=request.user,
                                                          certificate_template__course=enrollment.course)
                except Certificate.DoesNotExist:
                    msg = f"User {request.user} passed course {passed_course} but doesn't have certificate." \
                          f" Is this a feature, not a bug?"
                    logger.warning(msg)

        # Attach badge information...
        awards_badges = enrollment.course.enable_badges
        course_passed_badge_class = None
        badge_assertion = None
        if awards_badges:
            try:
                course_passed_badge_class = BadgeClass.objects.get(course=enrollment.course,
                                                                   type=BadgeClassType.COURSE_PASSED.name)
            except BadgeClass.DoesNotExist:
                pass
            if course_passed_badge_class:
                try:
                    badge_assertion = BadgeAssertion.objects.get(badge_class=course_passed_badge_class,
                                                                 recipient=request.user)
                    student_has_badges = True
                except BadgeAssertion.DoesNotExist:
                    pass

        # Other course information...
        user_can_access_course = can_access_course(user=request.user, course=enrollment.course)

        # Add to dictionary for context...
        course_info = {
            "enrollment": enrollment,
            "course": enrollment.course,
            "has_passed": passed_course,
            "certificate": certificate,
            "badge_assertion": badge_assertion,
            "course_awards_badges": awards_badges,
            "user_can_access_course": user_can_access_course,
            "course_passed_badge_class": course_passed_badge_class
        }
        courses_info.append(course_info)

    # Return list of courses, with addition of "passed" property
    context = {
        "user_badges_enabled": user_badges_enabled,
        "section": "dashboard",
        "title": "My Dashboard",
        "description": "A list of all the courses you're enrolled in or have taken in the past.",
        "courses_info": courses_info,
        "student_has_badges": student_has_badges
    }

    return render(request, 'dashboard/index.html', context)
