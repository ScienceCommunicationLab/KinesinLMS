import logging
from typing import Optional, OrderedDict, Type

from django.contrib.auth import get_user_model

from kinesinlms.assessments.forms import (
    DoneIndicatorForm,
    SubmittedAnswerForm,
    MultipleChoiceForm,
    LongFormTextEntryForm,
    PollForm,
)
from kinesinlms.assessments.models import Assessment, SubmittedAnswer
from kinesinlms.course.constants import CourseUnitType
from kinesinlms.course.models import Course
from kinesinlms.course.tasks import (
    remove_assessment_from_milestone_progress,
    rescore_assessment_milestone_progress,
)
from kinesinlms.learning_library.constants import BlockType, AssessmentType
from kinesinlms.learning_library.models import UnitBlock

logger = logging.getLogger(__name__)
User = get_user_model()


def get_answer_data(course: Course, assessment: Assessment, student):
    """
    Get the assessment slug, question text and
    student's answer from an Assessment-type block.

    Args:
        course:
        assessment:
        student:

    Returns:
        An object with student's answer, as well as the assessment's slug
        and the question text.

    """

    assert assessment is not None
    assert student is not None

    answers = SubmittedAnswer.objects.filter(
        student=student, course=course, assessment=assessment
    ).all()
    count = len(answers)
    if count >= 1:
        # should only be one, since student and assessment are unique_together
        if count > 1:
            logger.error(
                f"get_printable_review_data() User {student} has more than one answer for an assessment!"
            )
        # TODO: Get rid of first(). That's ugly.
        answer = answers.first()
        answer_text = answer.json_content.get("answer", None)
    else:
        answer_text = None
    answer_data = {
        "id": assessment.id,
        "slug": assessment.slug,
        "question": assessment.question,
        "question_as_statement": assessment.question_as_statement,
        "answer_text": answer_text,
    }

    return answer_data


def get_num_block_type_for_node(
    node: OrderedDict, block_type: BlockType, graded_only=False
) -> int:
    """
    Count the number of blocks in a node.

    Args:
        node:           Node instance to search
        block_type:     Type of block to be counted
        graded_only:    If block is ASSESSMENT or SIMPLE_INTERACTIVE_TOOL, this
                        flag indicates whether to count only graded blocks (True)
                        or all blocks (False)

    Returns:
        Integer for count
    """

    if (
        block_type.name
        not in [BlockType.ASSESSMENT.name, BlockType.SIMPLE_INTERACTIVE_TOOL.name]
        and graded_only
    ):
        raise ValueError(
            f"graded_only may only be True with "
            f"block_type {BlockType.ASSESSMENT.name} or {BlockType.SIMPLE_INTERACTIVE_TOOL.name}"
        )

    count = 0
    unit = node.get("unit")
    if unit:
        course_unit_id = unit.get("id")
        unit_type = unit.get("type")
        if course_unit_id and unit_type == CourseUnitType.STANDARD.name:
            blocks_qs = UnitBlock.objects.filter(
                course_unit__id=course_unit_id, read_only=False, block__type=block_type
            )
            if graded_only:
                if block_type.name == BlockType.ASSESSMENT.name:
                    blocks_qs = blocks_qs.filter(block__assessment__graded=True)
                elif block_type.name == BlockType.SIMPLE_INTERACTIVE_TOOL.name:
                    blocks_qs = blocks_qs.filter(
                        block__simple_interactive_tool__graded=True
                    )
                else:
                    raise ValueError(f"Unexpected block_type {block_type}")
            count += blocks_qs.count()
    node_children = node.get("children", [])
    for child_node in node_children:
        count += get_num_block_type_for_node(child_node, block_type, graded_only)

    return count


def get_submitted_answer_form_class(assessment) -> Type[SubmittedAnswerForm]:
    """
    Simple factory method to get the correct submitted
    answer form for this type of assessment.
    """
    if assessment.type == AssessmentType.DONE_INDICATOR.name:
        return DoneIndicatorForm
    elif assessment.type == AssessmentType.POLL.name:
        return PollForm
    elif assessment.type == AssessmentType.MULTIPLE_CHOICE.name:
        return MultipleChoiceForm
    elif assessment.type == AssessmentType.LONG_FORM_TEXT.name:
        return LongFormTextEntryForm
    else:
        raise NotImplementedError()


def delete_submitted_answers(
    course: Course,
    student: Optional[User] = None,
    assessment: Optional[Assessment] = None,
) -> int:
    """
    Delete all SubmittedAnswers for the given course + student (optional) + assessment (optional).
    """
    assert course
    answers = SubmittedAnswer.objects.filter(course=course)
    if student:
        answers = answers.filter(student=student)
    if assessment:
        answers = answers.filter(assessment=assessment)

    count, _deleted_data = answers.delete()

    # Update/delete any affected MilestoneProgress
    remove_assessment_from_milestone_progress.apply_async(
        args=[],
        kwargs={
            "course_id": course.id,
            "user_id": student.id if student else None,
            "assessment_id": assessment.id if assessment else None,
        },
    )

    return count


def rescore_submitted_answers(
    course: Course,
    student: Optional[User] = None,
    assessment: Optional[Assessment] = None,
) -> int:
    """
    Rescore all SubmittedAnswers for the given course + optionally student + assessment
    """
    assert course
    answers = SubmittedAnswer.objects.filter(course=course)
    if student:
        answers = answers.filter(student=student)
    if assessment:
        answers = answers.filter(assessment=assessment)

    # Rescore the assessment milestones relevant to these answers.
    rescore_assessment_milestone_progress.apply_async(
        args=[],
        kwargs={
            "course_id": course.id,
            "user_id": student.id if student else None,
            "assessment_id": assessment.id if assessment else None,
        },
    )

    return answers.count()
