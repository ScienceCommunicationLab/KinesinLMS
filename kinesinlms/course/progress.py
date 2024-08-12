import logging
from dataclasses import dataclass, field
from typing import List

from dataclasses_json import dataclass_json
from django.contrib.auth import get_user_model

from kinesinlms.assessments.models import SubmittedAnswer
from kinesinlms.course.constants import MilestoneType
from kinesinlms.course.models import CourseUnit, Milestone, MilestoneProgress
from kinesinlms.course.nav import get_course_nav
from kinesinlms.learning_library.constants import BlockType
from kinesinlms.sits.constants import SimpleInteractiveToolSubmissionStatus
from kinesinlms.sits.models import SimpleInteractiveToolSubmission

logger = logging.getLogger(__name__)

User = get_user_model()


@dataclass_json()
@dataclass
class ProgressItem:
    released: bool
    module_node_id: int
    module_node_content_index: int
    module_node_slug: str
    section_node_id: int
    section_node_content_index: int
    section_node_slug: str
    unit_node_id: int
    unit_node_content_index: int
    unit_node_slug: str
    title: str
    graded: bool = False
    completed: bool = False
    score: int = 0
    max_score: int = 0


@dataclass_json()
@dataclass
class MilestoneProgressData:
    message: str = ""
    items: List[ProgressItem] = field(default_factory=list)
    item_type: str = ''
    count_requirement: int = 0
    count_graded_only: bool = False
    min_score_requirement: int = 0
    progress_achieved: bool = False
    progress_count: int = 0
    progress_score_possible: int = 0
    progress_score_achieved: int = 0

    @property
    def item_count(self):
        return len(self.items)


@dataclass_json()
@dataclass
class ProgressStatus:
    milestones: List[MilestoneProgressData]

    @property
    def has_data(self):
        return any(
            len(milestone_progress.items) > 0
            for milestone_progress in self.milestones
        )


def get_progress_status(course: "kinesinlms.course.Course",
                        student,
                        target_module_node: "kinesinlms.course.CourseNode") -> ProgressStatus:
    """
       Create and return an instance of a ProgressDetail of dataclass,
       with information about milestone activity in the course and the student's status for it.
       Include module, section and unit information for the items
       (the first position it appears in the course).

       Args:
           course:
           student:
           target_module_node:     Limit to module node (if provided)

       Returns:
           A ProgressStatus dataclass instances.

       """

    if course is None:
        raise ValueError("Course must be defined")
    if student is None:
        raise ValueError("Student must be defined")

    milestone_data: List[MilestoneProgressData] = []

    milestones = Milestone.objects.filter(course=course,
                                          required_to_pass=True).order_by('type')
    for milestone in milestones:

        milestone_progress_data = get_milestone_progress_data(milestone,
                                                              course,
                                                              student,
                                                              target_module_node)

        milestone_data.append(milestone_progress_data)

    return ProgressStatus(milestones=milestone_data)


def get_milestone_progress_data(
        milestone: "kinesinlms.course.Milestone",
        course: "kinesinlms.course.Course",
        student,
        target_module_node: "kinesinlms.course.CourseNode") -> MilestoneProgressData:
    """
       Create and return an instance of a MilestoneProgressData dataclass,
       with information about milestone activity in the course and the student's status for it.
       Include module, section and unit information for the items
       (the first position it appears in the course).

       Args:
           milestone:
           course:
           student:
           target_module_node:     Limit to module node (if provided)

       Returns:
           A MilestoneProgressData dataclass instances.

    """
    milestone_progress_items: List = []
    milestone_progress_blocks: List[str] = []
    milestone_progress = milestone.progresses.filter(student=student).first()
    milestone_progress_score_possible = 0
    if milestone_progress:
        milestone_progress_blocks = milestone_progress.blocks.values_list('uuid', flat=True)

    course_nav = get_course_nav(course)
    module_nodes = course_nav.get('children', [])
    ignore_release_date = course.self_paced
    milestone_item_type = None
    total_graded_blocks = None

    for module_node in module_nodes:
        if target_module_node and module_node['id'] != target_module_node.id:
            continue

        section_nodes = module_node.get('children', [])
        for section_node in section_nodes:
            unit_nodes = section_node.get('children', [])
            for unit_node in unit_nodes:
                released = ignore_release_date or (released and unit_node['is_released'])
                try:
                    unit = CourseUnit.objects.get(id=unit_node['unit']['id'])
                except CourseUnit.DoesNotExist as dne:
                    raise dne

                unit_blocks = unit.contents
                total_graded_blocks = 0

                if milestone.type == MilestoneType.CORRECT_ANSWERS.name:
                    milestone_item_type = BlockType.ASSESSMENT.value
                    unit_blocks = unit_blocks.filter(
                        type=BlockType.ASSESSMENT.name
                    ).prefetch_related('assessment')

                elif milestone.type == MilestoneType.VIDEO_PLAYS.name:
                    milestone_item_type = BlockType.VIDEO.value
                    unit_blocks = unit_blocks.filter(
                        type=BlockType.VIDEO.name
                    )

                elif milestone.type == MilestoneType.SIMPLE_INTERACTIVE_TOOL_INTERACTIONS.name:
                    milestone_item_type = BlockType.SIMPLE_INTERACTIVE_TOOL.value
                    unit_blocks = unit_blocks.filter(
                        type=BlockType.SIMPLE_INTERACTIVE_TOOL.name
                    ).prefetch_related('simple_interactive_tool')

                else:
                    continue

                for block in unit_blocks:

                    graded = False
                    title = block.display_name
                    max_score = None
                    score = None

                    if milestone.type == MilestoneType.CORRECT_ANSWERS.name:
                        assessment = block.assessment
                        graded = assessment.graded
                        title = assessment.question or block.display_name
                        max_score = assessment.max_score
                        answer = assessment.answers.filter(course=course, student=student).first()
                        if answer:
                            score = answer.score

                    elif milestone.type == MilestoneType.SIMPLE_INTERACTIVE_TOOL_INTERACTIONS.name:
                        sit = block.simple_interactive_tool
                        graded = sit.graded
                        title = sit.display_name or block.display_name
                        max_score = sit.max_score
                        answer = sit.submissions.filter(course=course, student=student).first()
                        if answer:
                            score = answer.score

                    completed = block.uuid in milestone_progress_blocks
                    milestone_progress_score_possible += max_score
                    if graded:
                        total_graded_blocks += 1

                    block_progress = ProgressItem(
                        released=released,
                        module_node_id=module_node['id'],
                        module_node_content_index=module_node['content_index'],
                        module_node_slug=module_node['slug'],
                        section_node_id=section_node['id'],
                        section_node_content_index=section_node['content_index'],
                        section_node_slug=section_node['slug'],
                        unit_node_id=unit_node['id'],
                        unit_node_content_index=unit_node['content_index'],
                        unit_node_slug=unit_node['slug'],
                        title=title,
                        graded=graded,
                        completed=completed,
                        max_score=max_score,
                        score=score,
                    )
                    milestone_progress_items.append(block_progress)

    milestone_progress_data = MilestoneProgressData(
        items=milestone_progress_items,
        item_type=milestone_item_type,
        count_requirement=milestone.count_requirement,
        count_graded_only=milestone.count_graded_only,
        min_score_requirement=milestone.min_score_requirement,
        progress_score_possible=milestone_progress_score_possible,
    )

    if milestone_progress:
        milestone_progress_data.progress_achieved = milestone_progress.achieved
        milestone_progress_data.progress_count = milestone_progress.count
        milestone_progress_data.progress_score_achieved = milestone_progress.total_score

    if milestone_progress_data.count_graded_only:
        item_str = f"graded {milestone_item_type} items"
        total_blocks = total_graded_blocks
        total_score = milestone_progress_data.progress_score_achieved
    else:
        item_str = f"{milestone_item_type} items"
        total_blocks = milestone_progress_data.item_count
        total_score = milestone_progress_data.progress_score_achieved

    if milestone_progress_data.count_requirement:
        if milestone_progress_data.count_requirement == total_blocks:
            milestone_progress_data.message = (
                f"Milestone requirement: You must complete all "
                f"{milestone_progress_data.count_requirement} {item_str}"
            )
        else:
            milestone_progress_data.message = (
                f"Milestone requirement: You must complete "
                f"{milestone_progress_data.count_requirement}"
                f"of {total_blocks} {item_str}"
            )

    elif milestone_progress_data.min_score_requirement:
        if milestone_progress_data.min_score_requirement == total_score:
            milestone_progress_data.message += (
                f"Milestone requirement: You must score at least "
                f"{milestone_progress_data.min_score_requirement} "
                f"points total on {item_str}"
            )
        else:
            milestone_progress_data.message += (
                f"Milestone requirement: You must score at least "
                f"{milestone_progress_data.count_requirement} "
                f"of {total_score} points on {item_str}"
            )

    if milestone_progress_data.message:
        milestone_progress_data.message += "."

    return milestone_progress_data
