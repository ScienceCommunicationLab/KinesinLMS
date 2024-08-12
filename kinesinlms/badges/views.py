import logging
from io import BytesIO
from typing import Optional

import PIL.Image
import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponse, HttpResponseServerError
from django.shortcuts import render, get_object_or_404
from django.views.generic import FormView, ListView, DetailView
from rest_framework import status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound, APIException, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from kinesinlms.badges.forms import BadgeAssertionForm
from kinesinlms.badges.models import BadgeClass, BadgeAssertion, BadgeClassType
from kinesinlms.badges.utils import get_badge_service
from kinesinlms.course.models import CoursePassed, Enrollment
from kinesinlms.course.utils_access import can_access_course
from kinesinlms.course.view_helpers import access_denied_hx

logger = logging.getLogger(__name__)


# API CLASSES AND METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# DRF ViewSets
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class BadgeAssertionViewSet(viewsets.ViewSet):
    allowed_methods = ['POST']

    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def create(self, request):
        """
        The main purpose of exposing CREATE (post) behavior is
        to allow the user to generate a badge assertion for a course that
        offers badges and which they've already completed, but they
        don't have a badge for.
        """
        badge_class_id = request.data.get('badge_class_id', None)
        if badge_class_id:
            badge_class_id = int(badge_class_id)

        if not badge_class_id or BadgeClass.objects.filter(id=badge_class_id).count() == 0:
            raise NotFound(detail=f"Badge class id '{badge_class_id}' does not exist. ")

        badge_class = BadgeClass.objects.get(id=badge_class_id)

        # Make sure student is allowed to request a badge
        # generation for this badge class.
        student = request.user
        settings = student.get_settings()
        if not settings.enable_badges:
            error_msg = "User does not have badges enabled in their settings."
            logger.error(f"BadgeAssertionViewSet create(): {error_msg}")
            raise PermissionDenied(detail=error_msg)

        # Make sure the course offers badges...
        course = badge_class.course
        if not course.enable_badges:
            error_msg = f"Course {course.token} does not award badges."
            logger.error(f"BadgeAssertionViewSet create(): {error_msg}")
            raise PermissionDenied(detail=error_msg)

        # Make sure they passed...
        try:
            CoursePassed.objects.get(course=course,
                                     student=request.user)
        except CoursePassed.DoesNotExist:
            error_msg = f"User has not passed course {course.token}"
            logger.error(f"BadgeAssertionViewSet create(): {error_msg}")
            raise PermissionDenied(detail=error_msg)

        # If assertion already exists, just return it.
        if BadgeAssertion.objects.filter(badge_class=badge_class, recipient=student).count() > 0:
            badge_assertion = BadgeAssertion.objects.get(badge_class=badge_class, recipient=student)
            return Response({'badge_assertion_id': badge_assertion.id}, status=status.HTTP_200_OK)

        # Try to award assertion
        try:
            badge_service = get_badge_service()
            badge_assertion: BadgeAssertion = badge_service.issue_badge_assertion(badge_class=badge_class,
                                                                                  recipient=student)
            if not badge_assertion:
                error_msg = "No badge_assertion was returned from issue_badge_assertion()"
                logger.error(f"BadgeAssertionViewSet create(): {error_msg}")
                raise APIException("Error generating badge assertion. Please contact support.")
        except Exception:
            error_msg = "generate_badge_assertion() Could not create badge assertion"
            logger.exception(f"BadgeAssertionViewSet create(): {error_msg}")
            raise APIException("Error generating badge assertion. Please contact support.")

        return Response({'badge_assertion_id': badge_assertion.id}, status=status.HTTP_200_OK)

    def list(self, request):
        raise APIException("Not implemented")

    def retrieve(self, request, pk=None):
        raise APIException("Not implemented")

    def update(self, request, pk=None):
        raise APIException("Not implemented")

    def partial_update(self, request, pk=None):
        raise APIException("Not implemented")

    def destroy(self, request, pk=None):
        raise APIException("Not implemented")


# VIEW CLASSES AND METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class BadgeClassListView(UserPassesTestMixin, ListView):
    context_object_name = 'badge_classes'
    template_name = 'badges/badge_class_list.html'
    queryset = BadgeClass.objects.all()
    raise_exception = True

    def test_func(self):
        return self.request.user.is_staff


class BadgeClassDetailView(UserPassesTestMixin, DetailView):
    context_object_name = 'badge_class'
    template_name = 'badges/badge_class_detail.html'
    queryset = BadgeClass.objects.all()
    raise_exception = True

    def test_func(self):
        return self.request.user.is_staff


class BadgeAssertionFormView(UserPassesTestMixin, FormView):
    """
    This view is only for admins. It allows the admin to create
    a badge assertion for a user.
    """

    template_name = 'badges/create_badge_assertion.html'
    form_class = BadgeAssertionForm
    raise_exception = True

    def form_valid(self, form):
        response = super().form_valid(form)

        logger.debug("Created local BadgeAssertion class. Now attempting to create assertion in remote service....")
        # Create external badge assertion
        badge_assertion: BadgeAssertion = form.instance
        try:
            service = get_badge_service()
            service.create_remote_badge_assertion(badge_assertion=badge_assertion)
            logger.debug(f"Created badge assertion in remote service : {badge_assertion.open_badge_id}")
        except Exception as e:
            logger.exception("Could not create badge assertion in remote service")
            badge_assertion.error_message = str(e)
            badge_assertion.save()

        logger.debug(f"Created new badge assertion {badge_assertion}")

        return response

    def test_func(self):
        return self.request.user.is_staff


@login_required
def download_badge_assertion_image(request,
                                   badge_class_id: int,
                                   badge_assertion_id: int):
    """ Allow a student to directly download the badge ID.

    As part of this request will load the badge ID from Badgr.

    """

    badge_assertion = get_object_or_404(BadgeAssertion,
                                        id=badge_assertion_id,
                                        badge_class_id=badge_class_id,
                                        recipient=request.user)

    badge_image_url = badge_assertion.badge_image_url

    resp = requests.get(badge_image_url, stream=True)
    if not resp or resp.status_code != requests.codes.ok:
        logger.error(f"Could not download badge assertion {badge_assertion_id} "
                     f"for student {request.user}. Status code : {resp.status_code}")
        msg = "Could not download badge image. Please visit badge page directly."
        messages.add_message(request, messages.ERROR, msg)
        return render(request, "badges/badge_image_not_found.html", {})

    if "svg" in resp.headers['Content-Type']:
        badge_download_response = HttpResponse(resp.content, content_type='image/svg')
        image_filename = f"{badge_assertion.badge_class.slug}.svg"
    else:
        try:
            image = PIL.Image.open(BytesIO(resp.content))
        except Exception as e:
            logger.exception(f"Could not transform badge bytes into image : {e}")
            return HttpResponseServerError("Error downloading badge. Please contact support.")
        image_bytes = BytesIO()
        image.save(image_bytes, format="PNG")
        badge_download_response = HttpResponse(image_bytes.getvalue(), content_type='image/png')
        image_filename = f"{badge_assertion.badge_class.slug}.png"

    badge_download_response['Content-Disposition'] = f"attachment; filename={image_filename}"
    return badge_download_response


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# HTMX VIEW METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# HTML Veiw Functions

@login_required
def badge_assertion_status_hx(request, badge_class_id: int, pk: int):
    """
    Return the badge assertion, including its status.

    Args:
        request:            ( request from badge_assetion_control.html template )
        badge_class_id:     The ID of the badge class to create an assertion for.
        pk:                 The ID of the badge assetion for this badge class.

    Returns:
        HTTP Response

    """

    badge_class = get_object_or_404(BadgeClass, id=badge_class_id, type=BadgeClassType.COURSE_PASSED.name)
    try:
        # Overspecified query to make sure request is legit
        badge_assertion = BadgeAssertion.objects.get(id=pk, badge_class=badge_class, recipient=request.user)
    except BadgeAssertion.DoesNotExist:
        badge_assertion = None

    context = {
        'course': badge_class.course,
        'course_passed_badge_class': badge_class,
        'badge_assertion': badge_assertion,
        'badge_generation_error': badge_assertion.error_message if badge_assertion else None
    }

    return render(request, 'badges/badge_assertion/badge_assertion_control.html', context)


@login_required
def create_badge_assertion_hx(request, pk: int):
    """
    Allows student to request a badge assertion for completing a course
    if they don't already have one.

    Args:
        request:        ( request from badge_assetion_control.html template )
        pk:             The ID of the badge class to create an assertion for.
                        This should be of type COURSE_PASSED.

    Returns:
        HTTP Response
    """
    if not pk:
        raise ValueError("Badge class ID is required.")

    badge_class = get_object_or_404(BadgeClass, id=pk, type=BadgeClassType.COURSE_PASSED.name)
    try:
        enrollment = Enrollment.objects.get(student=request.user, course=badge_class.course, active=True)
        if not can_access_course(request.user, badge_class.course, enrollment=enrollment):
            raise Exception("User does not have access to this course.")
    except Exception:
        logger.exception(f"create_badge_assertion_hx() Could not get badge class {id} for user {request.user}")
        return access_denied_hx(request=request,
                                course_slug=badge_class.course.slug,
                                course_run=badge_class.course.run)

    context = {
        'course': badge_class.course,
        'course_passed_badge_class': badge_class
    }

    # Return assertion if it already exists.
    try:
        badge_assertion: Optional[BadgeAssertion] = BadgeAssertion.objects.get(badge_class=badge_class, recipient=request.user)
    except BadgeAssertion.DoesNotExist:
        badge_assertion = None

    # If assertion doesn't exist, try to create it.
    error_for_user = None
    if badge_assertion and badge_assertion.open_badge_id is None:
        # If the assertion exists but doesn't have an ID, it probably failed
        # so delete it and try again.
        badge_assertion.delete()
        badge_assertion = None

    if not badge_assertion:

        try:
            # Don't do this async because this is an HMTx request so only
            # operation really is to generate badge, which shouldn't take that long.
            # Let's expect badge service to do it within e.g. Heroku 30 second time limit.
            badge_service = get_badge_service()
            badge_assertion: BadgeAssertion = badge_service.issue_badge_assertion(badge_class=badge_class,
                                                                                  recipient=request.user,
                                                                                  do_async=False)
            if not badge_assertion:
                error_msg = "No badge_assertion was returned from issue_badge_assertion()"
                logger.error(f"BadgeAssertionViewSet create(): {error_msg}")
                error_for_user = "Error generating badge assertion. Please contact support."
        except Exception:
            error_msg = "generate_badge_assertion() Could not create badge assertion"
            logger.exception(f"BadgeAssertionViewSet create(): {error_msg}")
            error_for_user = "Error generating badge assertion. Please contact support."

    context['badge_assertion'] = badge_assertion
    context["badge_generation_error"] = error_for_user

    return render(request, 'badges/badge_assertion/badge_assertion_control.html', context)
