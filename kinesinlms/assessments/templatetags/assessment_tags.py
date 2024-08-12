import logging

from django import template

from kinesinlms.assessments.utils import get_submitted_answer_form_class

register = template.Library()
logger = logging.getLogger(__name__)


@register.simple_tag(takes_context=True)
def build_submitted_answer_form(context, assessment, student, course, course_unit):
    """
    Creates and populates the correct SubmittedAnswer form for
    the given assessment (and submitted answer, if any).
    """

    block_view_context = context.get('block_view_context', None)
    block_view_mode = context.get('block_view_mode', None)
    SubmittedAnswerForm = get_submitted_answer_form_class(assessment)
    course_unit_id = course_unit.id
    form = SubmittedAnswerForm(assessment=assessment,
                               student=student,
                               course=course,
                               block_view_mode=block_view_mode,
                               block_view_context=block_view_context,
                               initial={
                                   "course_unit_id": course_unit_id
                               })
    return form
