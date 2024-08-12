import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Callable, Optional

import pandas as pd
from dataclasses_json import dataclass_json
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django_pandas.io import read_frame

from kinesinlms.assessments.models import SubmittedAnswer
from kinesinlms.course.models import Course, CoursePassed
from kinesinlms.learning_library.constants import BlockType
from kinesinlms.sits.constants import SimpleInteractiveToolSubmissionStatus
from kinesinlms.sits.models import SimpleInteractiveToolSubmission
from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.models import TrackingEvent

User = get_user_model()
logger = logging.getLogger(__name__)


@dataclass_json
@dataclass
class BarColors:
    units: str = "#3d8bfd"
    videos: str = "#479f76"
    assessments: str = "#ffcd39"
    sits: str = "#fda214"
    background: str = "#eeeeee"
    surveys: str = "#39ff58"


@dataclass_json
@dataclass
class ModuleInfo:
    module_node_id: int = 0
    # Some modules are missing the content_index
    # even though they should all have it defined.
    content_index: Optional[int] = 0
    display_sequence: int = 0
    module_slug: str = ""
    display_name: str = ""
    course_unit_ids: List[int] = field(default_factory=list)
    assessment_ids: List[int] = field(default_factory=list)
    video_block_uuids: List[str] = field(default_factory=list)
    sit_ids: List[int] = field(default_factory=list)


@dataclass_json
@dataclass
class StudentModuleProgress:
    module_info: ModuleInfo
    units_viewed: int = 0
    watched_videos: int = 0
    answered_assessments: int = 0
    answered_sits: int = 0

    @property
    def total_units_in_module(self) -> int:
        return len(self.module_info.course_unit_ids)

    @property
    def total_videos_in_module(self) -> int:
        return len(self.module_info.video_block_uuids)

    @property
    def total_assessments_in_module(self) -> int:
        return len(self.module_info.assessment_ids)

    @property
    def total_sits_in_module(self) -> int:
        num = len(self.module_info.sit_ids)
        return num

    @property
    def units_viewed_percent_complete(self) -> int:
        if not self.total_assessments_in_module:
            return 0
        return round((self.units_viewed / self.total_units_in_module) * 100)

    @property
    def videos_percent_complete(self) -> int:
        if not self.total_videos_in_module:
            return 0
        return round((self.watched_videos / self.total_videos_in_module) * 100)

    @property
    def assessments_percent_complete(self) -> int:
        if not self.total_assessments_in_module:
            return 0
        return round(
            (self.answered_assessments / self.total_assessments_in_module) * 100
        )

    @property
    def sits_percent_complete(self) -> int:
        if not self.total_sits_in_module:
            return 0
        return round((self.answered_sits / self.total_sits_in_module) * 100)


@dataclass_json
@dataclass
class StudentModulesProgress:
    student_id: int
    name: str
    username: str
    email: Optional[str] = None
    has_passed: bool = False
    modules_progress: List[StudentModuleProgress] = field(default_factory=list)


def get_student_module_progress(
    course: Course, students: QuerySet, progress_callback: Callable
) -> Tuple[List[ModuleInfo], List[StudentModulesProgress]]:
    """
    Gather information on student progress across each module of
    a course and report back as a dataclass.

    Args:
        course:
        students:
        progress_callback:

    """

    # Build up list of dataclasses here for modules
    # we care about. We do this rather than just querying
    # MPTT course_root because we might want to modify which
    # nodes we care about...so best to do it here where we're
    # building up student responses for relevant mdoules.
    modules_info: List[ModuleInfo] = []
    module_nodes = course.course_root_node.get_children()
    progress_callback("Processing course nodes...")
    for module_node in module_nodes:
        module_info = ModuleInfo(
            module_node_id=module_node.id,
            content_index=module_node.content_index,
            display_sequence=module_node.display_sequence,
            display_name=module_node.display_name,
            module_slug=module_node.slug,
        )
        modules_info.append(module_info)
        # Build up counts of :
        # -assessments
        # -videos
        # -SITs
        for section_node in module_node.children.order_by("display_sequence").all():
            for unit_node in section_node.children.order_by("display_sequence").all():
                module_info.course_unit_ids.append(unit_node.unit.id)
                unit = unit_node.unit
                for unit_block in unit.unit_blocks.all():
                    block = unit_block.block
                    block_type = block.type
                    if block_type == BlockType.VIDEO.name:
                        block_uuid = str(block.uuid)
                        module_info.video_block_uuids.append(block_uuid)
                    elif (
                        block_type == BlockType.ASSESSMENT.name
                        and unit_block.read_only is False
                    ):
                        module_info.assessment_ids.append(block.assessment.id)
                    elif (
                        block_type == BlockType.SIMPLE_INTERACTIVE_TOOL.name
                        and unit_block.read_only is False
                    ):
                        module_info.sit_ids.append(block.simple_interactive_tool.id)

    students = students.order_by("username").all()

    # Make a TrackingEvent lookup so that we don't do lots of queries against the TrackingEvent table
    tracking_event_types = [
        TrackingEventType.COURSE_PAGE_VIEW.value,
        TrackingEventType.COURSE_VIDEO_ACTIVITY.value,
    ]
    tracking_events = TrackingEvent.objects.filter(
        event_type__in=tracking_event_types, user__in=students, course_slug=course.slug
    ).all()

    df = read_frame(tracking_events)
    df["course_unit_id"] = df["course_unit_id"].fillna(0)
    df["block_uuid"] = df["block_uuid"].fillna(0)
    convert_dict = {"course_unit_id": int, "block_uuid": str}
    df = df.astype(convert_dict)

    num_students = len(students)
    count = 0
    students_modules_progresses: List[StudentModulesProgress] = []
    for student in students:
        count += 1
        if count % 10 == 0:
            percent_complete = round((count / num_students) * 100)
            progress_callback(
                f"Processing student activity ( {count} of {num_students} students )",
                percent_complete=percent_complete,
            )
        modules_progress: List[StudentModuleProgress] = []
        for module_info in modules_info:
            student_module_progress = StudentModuleProgress(module_info=module_info)
            modules_progress.append(student_module_progress)

            student_events_df = df[df["user"] == student.username]

            # Units Viewed
            units_viewed_df = student_events_df.loc[
                student_events_df["course_unit_id"].isin(module_info.course_unit_ids)
            ]
            units_viewed = len(pd.unique(units_viewed_df["course_unit_id"]))
            student_module_progress.units_viewed = units_viewed

            # Videos played
            videos_played_df = student_events_df.loc[
                student_events_df["block_uuid"].isin(module_info.video_block_uuids)
            ]
            num_videos = len(pd.unique(videos_played_df["block_uuid"]))
            student_module_progress.watched_videos = num_videos

            # Assessments answered
            num_student_answers = SubmittedAnswer.objects.filter(
                course=course,
                assessment__in=module_info.assessment_ids,
                student=student,
            ).count()
            student_module_progress.answered_assessments = num_student_answers

            if student.username == "scully35mm":
                logger.debug("Check count")

            # SITSs answered
            qs = SimpleInteractiveToolSubmission.objects.filter(
                course=course,
                simple_interactive_tool__in=module_info.sit_ids,
                status=SimpleInteractiveToolSubmissionStatus.COMPLETE.name,
                student=student,
            )
            num_student_sit_answered = qs.count()
            student_module_progress.answered_sits = num_student_sit_answered

        has_passed = CoursePassed.objects.filter(
            student=student, course=course
        ).exists()

        smsp = StudentModulesProgress(
            student_id=student.id,
            name=student.name,
            email=student.email,
            username=student.username,
            has_passed=has_passed,
            modules_progress=modules_progress,
        )

        students_modules_progresses.append(smsp)

    return modules_info, students_modules_progresses
