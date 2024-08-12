import logging
from typing import Type

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.forms import ModelForm
from django.http import HttpResponseForbidden, Http404
from django.shortcuts import get_object_or_404, render
from rest_framework import viewsets, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from kinesinlms.assessments.forms import SubmittedAnswerForm
from kinesinlms.assessments.models import Assessment, SubmittedAnswer
from kinesinlms.assessments.serializers import SubmittedAnswerSerializer, AssessmentSerializer
from kinesinlms.assessments.utils import get_submitted_answer_form_class
from kinesinlms.assessments.tracking import track_answer_submission
from kinesinlms.course.tasks import track_milestone_progress
from kinesinlms.course.models import CourseNode
from kinesinlms.course.view_helpers import process_course_hx_request
from kinesinlms.learning_library.constants import AnswerStatus

logger = logging.getLogger(__name__)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# API Classes and Methods
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class AssessmentViewSet(viewsets.ModelViewSet):
    serializer_class = AssessmentSerializer

    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAdminUser,)

    def get_queryset(self, *args, **kwargs):
        if self.request.user.is_superuser:
            return Assessment.objects.all()
        else:
            return None

    def create(self, request, pk=None, *args, **kwargs):
        response = {'message': 'Update function is not offered in this path.'}
        return Response(response, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request, pk=None, *args, **kwargs):
        response = {'message': 'Update function is not offered in this path.'}
        return Response(response, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, pk=None, *args, **kwargs):
        response = {'message': 'Update function is not offered in this path.'}
        return Response(response, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, pk=None, *args, **kwargs):
        response = {'message': 'Delete function is not offered in this path.'}
        return Response(response, status=status.HTTP_405_METHOD_NOT_ALLOWED)


class SubmittedAnswerViewSet(viewsets.ModelViewSet):
    serializer_class = SubmittedAnswerSerializer

    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self, *args, **kwargs):
        if self.request.user.is_superuser:
            return SubmittedAnswer.objects.all()
        else:
            return SubmittedAnswer.objects.all().filter(student=self.request.user)

    def partial_update(self, request, pk=None, **kwargs):
        response = {'message': 'Update function is not offered in this path.'}
        return Response(response, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, pk=None, **kwargs):
        response = {'message': 'Delete function is not offered in this path.'}
        return Response(response, status=status.HTTP_405_METHOD_NOT_ALLOWED)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# HTMX VIEW METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@login_required
def assessment_submission_hx(request,
                             course_slug=None,
                             course_run=None,
                             module_slug=None,
                             section_slug=None,
                             unit_slug=None,
                             pk=None):
    """
    Handle an HTMx submission of an assessment. The response will replace the
    assessment submission form with a message indicating that the submission
    was successful or unsuccessful.

    Note that this route includes module_slug, section_slug and unit_slug.
    We may need to use those to determing the exact unit that the assessment
    appears in. But otherwise that information can be ignored if it doesn't
    affect how the Assessment behaves when processing a submitted answer.

    This view expects the request to include the appropriate form
    for the type of assessment.

    IMPORTANT:
    The end goal is to have all assessments use this HTMx view and get rid of
    React implementations for all but the most complex assessments. But for now
    only the DoneIndicatorForm is using this view. The other assessments are
    still implemented in React.

    """

    try:
        course, enrollment, course_nav, unit_nav_info = process_course_hx_request(
            request,
            course_slug=course_slug,
            course_run=course_run,
            module_slug=module_slug,
            section_slug=section_slug,
            unit_slug=unit_slug)
    except PermissionDenied:
        logger.exception("User does not have permission to call this htmx endpoint")
        return HttpResponseForbidden("You do not have permission to perform the requested action.")
    except Exception:
        logger.exception("Could not process course htmx request")
        raise Http404("Error processing your request")

    if course.has_finished:
        return HttpResponseForbidden("This course has finished. "
                                     "Assessment submissions are not allowed.")

    assessment = get_object_or_404(Assessment, pk=pk)

    # Use the correct type of form for this assessment.
    # At the moment this is just proof-of-concept with one
    # assessment (Done Indicator) implemented, but eventually
    # we'll need to handle all types of assessments.
    form_class: Type[SubmittedAnswerForm] = get_submitted_answer_form_class(assessment)

    form = form_class(request.POST,
                      assessment=assessment,
                      student=request.user,
                      course=course)

    if form.is_valid():

        submitted_answer = form.save()

        # Track before doing milestone, in case there's an error
        try:
            unit_node = CourseNode.objects.get(pk=unit_nav_info.unit_node_id)
            course_unit = unit_node.unit
        except Exception:
            course_unit = None

        try:
            track_answer_submission(submitted_answer=submitted_answer, course_unit=course_unit)
        except Exception:
            logger.exception(f"Could not track answer submission for answer {submitted_answer} ")

        # Update the milestone counters, if applicable.
        if submitted_answer.status != AnswerStatus.UNANSWERED.name:
            try:
                track_milestone_progress.apply_async(
                    args=[],
                    kwargs={
                        "course_id": submitted_answer.course.id,
                        "user_id": submitted_answer.student.id,
                        "block_uuid": submitted_answer.assessment.block.uuid,
                        "submission_id": submitted_answer.id,
                        "previous_answer_status": form.previous_answer_status,
                    },
                )
            except Exception:
                logger.exception(f"Could not update milestone for answer {submitted_answer} ")
                # TODO :
                #   How should we handle submission if we can't track progress?
                #   Should we still allow?
    else:
        submitted_answer = None

    context = {
        'form': form,
        'course': course,
        'module_slug': module_slug,
        'section_slug': section_slug,
        'unit_slug': unit_slug,
        'block': assessment.block,
        'assessment': assessment,
        'submitted_answer': submitted_answer
    }

    partial_htmx_template = f"course/blocks/assessment/{assessment.type.lower()}_hx.html"

    return render(request, partial_htmx_template, context)
