from typing import Optional
import logging

from kinesinlms.assessments.models import SubmittedAnswer, Assessment
from kinesinlms.course import course_passed_service
from kinesinlms.course.constants import MilestoneType
from kinesinlms.course.exceptions import CourseFinishedException
from kinesinlms.course.models import Course, MilestoneProgress, CoursePassed
from kinesinlms.learning_library.constants import ANSWER_STATUS_FINISHED, BlockType
from kinesinlms.learning_library.models import Block
from kinesinlms.sits.constants import SimpleInteractiveToolSubmissionStatus
from kinesinlms.sits.models import SimpleInteractiveToolSubmission
from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.tracker import Tracker
from kinesinlms.users.models import User

logger = logging.getLogger(__name__)


class MilestoneMonitor:
    """
    Encapsulate code that knows when to mark milestones
    as "achieved" and when a student has passed a course
    after achieving all required milestones.
    """

    @classmethod
    def track_interaction_by_id(
        cls,
        course_id: int,
        user_id: int,
        block_uuid: str,
        **kwargs,
    ) -> bool:
        """
        Tracks progress towards the affected course milestones.

        Args:
            course_id:       ID of current course.
            user_id:         ID of User who just validated their email (and therefore has successfully registered)
            block_uuid:      UUID of the Block the user interacted with
            kwargs:          extra arguments to pass to tracking method, must be serializable.

        Returns:
            Boolean flag representing success of operation
        """
        assert course_id is not None
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            logger.error(
                f"Cannot track event for course id {course_id} as course does not exist."
            )
            return False

        assert user_id is not None
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(
                f"Cannot track event for user {user_id} as user does not exist."
            )
            return False

        assert block_uuid is not None
        try:
            block = Block.objects.get(uuid=block_uuid)
        except Block.DoesNotExist:
            logger.error(
                f"Cannot track event for block {block_uuid} as block does not exist."
            )
            return False

        try:
            just_achieved = cls.track_interaction(
                course=course, student=user, block=block, **kwargs
            )
            logger.debug(
                f"track_milestone_progress() Tracked event "
                f"just_achieved: {just_achieved}"
            )
        except CourseFinishedException:
            logger.info(
                f"FAILED. No tracking simple milestone interaction for "
                f"course {course_id} user : {user_id} as course is finished"
            )
            return False

        except Exception:
            logger.exception("Could not track event!")
            return False

        return True

    @classmethod
    def track_interaction(
        cls,
        course: Course,
        student: User,
        block: Block,
        **kwargs,
    ) -> bool:
        """
        Check the progress towards the appropriate milestones for the given block.

        Args:
            course:         Course object
            student:        User object
            block:          Block object
            kwargs:         extra arguments for specific interactions.

        Returns:
             -  a boolean flag indicating whether the student just achieved the
                requirements of any assessment Milestone.

        Raises:
            ValueError if arguments not provided as expected.
            NotImplementedError if no method present to check type of item.

        """

        if not course:
            raise ValueError("Course argument cannot be None")
        if not student:
            raise ValueError("Student argument cannot be None")
        if not block:
            raise ValueError("Block argument cannot be None")

        if course.has_finished:
            raise CourseFinishedException(
                "Cannot track interaction: Course has already finished."
            )

        # Define some flags before checking milestones
        any_milestone_achieved = False
        check_for_course_passed = False

        # Default score for a block is 1 -- Assessments or SITs may differ.
        item_score = 1
        milestones = course.milestones
        # Default block status is "graded" -- Assessments or SITs may differ.
        graded = True

        # Simple milestones
        if block.type == BlockType.VIDEO.name:
            milestones = milestones.filter(type=MilestoneType.VIDEO_PLAYS.name)

        # Forum milestones
        elif block.type == BlockType.FORUM_TOPIC.name:
            # TODO -- any validation to do here?

            milestones = milestones.filter(type=MilestoneType.FORUM_POSTS.name)

        # SIT milestones
        elif block.type == BlockType.SIMPLE_INTERACTIVE_TOOL.name:
            # Skip updating progress if the submission is invalid or not complete.
            submission = cls._validate_sit_submission(**kwargs)
            if not submission:
                return False

            item_score = submission.score
            graded = submission.simple_interactive_tool.graded
            milestones = milestones.filter(
                type=MilestoneType.SIMPLE_INTERACTIVE_TOOL_INTERACTIONS.name
            )

        # Assessment milestones
        elif block.type == BlockType.ASSESSMENT.name:
            # Skip updating progress if the answer is invalid or not complete.
            submission = cls._validate_answer_submission(**kwargs)
            if not submission:
                return False

            item_score = submission.score
            graded = submission.assessment.graded
            milestones = milestones.filter(type=MilestoneType.CORRECT_ANSWERS.name)

        else:
            logger.debug(f"No course milestones exist for {block.type}, skipping.")
            return False

        if not milestones.count():
            logger.debug(f"No course milestones found for {block.type}, skipping.")
            return False

        # Update milestone progress
        for milestone in milestones.all():
            if milestone.count_graded_only and not graded:
                logger.info(
                    f"MilestoneMonitor: milestone {milestone} only counts graded but  "
                    f"{block} is not graded, so ignoring for this milestone."
                )
                continue

            progress, _created = MilestoneProgress.objects.get_or_create(
                course_id=course.id, milestone_id=milestone.id, student_id=student.id
            )

            if progress.achieved:
                logger.debug("Student has already achieved this milestone, skipping.")
                continue

            old_count = progress.count
            new_count, just_achieved = progress.add_block(block, item_score)

            milestone = progress.milestone
            if just_achieved:
                any_milestone_achieved = True

                Tracker.track(
                    event_type=TrackingEventType.MILESTONE_COMPLETED.value,
                    user=student,
                    event_data={
                        "milestone_type": milestone.type,
                        "milestone_id": milestone.id,
                    },
                    course=course,
                )

                if milestone.required_to_pass:
                    check_for_course_passed = True

            elif old_count < new_count:
                Tracker.track(
                    event_type=TrackingEventType.MILESTONE_PROGRESSED.value,
                    user=student,
                    event_data={
                        "milestone_type": milestone.type,
                        "milestone_id": milestone.id,
                    },
                    course=course,
                )

        # Mark course passed if we can
        if check_for_course_passed:
            awarded_course_passed = cls._award_course_passed_if_course_passed(
                course=course, student=student
            )
            if awarded_course_passed:
                logger.debug(
                    "f  - after this interaction, student was awarded course passed."
                )

        logger.debug(
            f"MilestoneMonitor: Checked student progress towards {len(milestones)} milestones"
        )

        return any_milestone_achieved

    @classmethod
    def remove_assessment_from_progress_by_id(
        cls,
        course_id: int,
        user_id: Optional[int] = None,
        assessment_id: Optional[int] = None,
    ) -> int:
        """
        Wrapper for remove_assessment_from_progress which takes IDs as parameters,
        so this function can be invoked from a celery task.

        See remove_assessment_from_progress for more details.

        Args:
            course_id (required)
            user_id (optional) ID of student, limits affected MilestoneProgress to just this student.
            assessment_id (optional) ID of assessment to remove from MilestoneProgress.

        Returns:
            number of MilestoneProgress objects updated or deleted.

        """
        count = 0
        assert course_id is not None
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return count

        user = None
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return count

        assessment = None
        if assessment_id:
            try:
                assessment = Assessment.objects.select_related("block").get(
                    id=assessment_id
                )
            except Assessment.DoesNotExist:
                return count

        try:
            count = cls.remove_assessment_from_progress(
                course=course, student=user, assessment=assessment
            )
        except CourseFinishedException:
            pass

        return count

    @classmethod
    def remove_assessment_from_progress(
        cls,
        course: Course,
        student: Optional[User] = None,
        assessment: Optional[Assessment] = None,
    ) -> int:
        """
        Efficiently removes assessment block(s) from the relevant MilestoneProgress objects,
        and adjusts their block count and total_score accordingly.

        Like MilestoneProgress.remove_block, it DOES NOT adjust completion.
        Assumes that once a student completes something, they don't lose it.

        Args:
            course (required)   Course to remove assessment from.
            student:            User (optional) limit affected MilestoneProgress to just this student.
            assessment:         Assessment to remove from MilestoneProgress.

        Returns:
            number of MilestoneProgress objects updated or deleted.
            CourseFinishedException if the course has finished.

        """
        assert course
        if course.has_finished:
            raise CourseFinishedException(
                "Cannot track interaction: Course has already finished."
            )

        # Update only Assessment-related progress items
        progresses = MilestoneProgress.objects.filter(
            course=course, milestone__type=MilestoneType.CORRECT_ANSWERS.name
        )
        if student:
            progresses = progresses.filter(student=student)

        # If we're deleting a single assessment, we need to update all affected MilestoneProgress.
        if assessment:
            # Updating all students' MilestoneProgress could be expensive, so we do it in bulk.
            return MilestoneProgress.bulk_remove_block(
                progresses=progresses, block=assessment.block
            )

        # Otherwise we're deleting progress for all assessments,
        # so we can delete all the MilestoneProgress too.
        else:
            total_count, deleted_data = progresses.delete()
            count = deleted_data.get("course.MilestoneProgress", 0)

        return count

    @classmethod
    def rescore_assessment_progress_by_id(
        cls,
        course_id: int,
        user_id: Optional[int] = None,
        assessment_id: Optional[int] = None,
    ) -> int:
        """
        Wrapper for rescore_assessment_progress which takes IDs as parameters,
        so this function can be invoked from a celery task.

        See rescore_assessment_progress for more details.

        Args:
            course_id (required)
            user_id (optional) ID of student, limits affected MilestoneProgress to just this student.
            assessment_id (optional) ID of assessment, limits affected MilestoneProgress to just this assessment.

        Returns:
            number of MilestoneProgress objects updated.
        """
        count = 0
        assert course_id is not None
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return count

        user = None
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return count

        assessment = None
        if assessment_id:
            try:
                assessment = Assessment.objects.select_related("block").get(
                    id=assessment_id
                )
            except Assessment.DoesNotExist:
                return count

        logger.debug(
            f"Rescoring assessments for course={course}, student={user_id}, assessment={assessment_id}"
        )

        try:
            count = cls.rescore_assessment_progress(
                course=course, student=user, assessment=assessment
            )
        except CourseFinishedException:
            pass

        return count

    @classmethod
    def rescore_assessment_progress(
        cls,
        course: Course,
        student: Optional[User] = None,
        assessment: Optional[Assessment] = None,
    ) -> int:
        """
        Efficiently re-grades and re-scores the course's assessment(s) against the relevant MilestoneProgress objects,
        and adjusts their block count and total_score accordingly.

        This function may mark MilestoneProgress objects as "achieved", but
        like MilestoneProgress.remove_block, it DOES NOT remove completion.
        Assumes that once a student completes something, they don't lose it.

        Args:
            course (required)
            student: User (optional)                limit affected MilestoneProgress to just this student.
            assessment: Optional[Assessment]

        Returns:
            number of MilestoneProgress objects updated.
            CourseFinishedException if the course has finished.
        """
        assert course
        if course.has_finished:
            raise CourseFinishedException(
                "Cannot rescore assessments: Course has already finished."
            )

        block = None
        if assessment:
            block = assessment.block

        # Update only Assessment-related MilestoneProgress objects.
        progresses = MilestoneProgress.objects.filter(
            course=course, milestone__type=MilestoneType.CORRECT_ANSWERS.name
        )
        if student:
            progresses = progresses.filter(student=student)
        if assessment:
            progresses = progresses.filter(blocks__in=[assessment.block_id])

        # Fetch related objects to reduce query count during rescoring.
        progresses = progresses.select_related("milestone", "course", "student")

        count = 0

        for progress in progresses:
            just_achieved = progress.rescore(block=block)

            if just_achieved and progress.milestone.required_to_pass:
                awarded_course_passed = cls._award_course_passed_if_course_passed(
                    course=progress.course, student=progress.student
                )
                if awarded_course_passed:
                    logger.debug(
                        "f  - after this rescoring, student was awarded course passed."
                    )

            count += 1

        return count

    # ~~~~~~~~~~~~~~~~~~~~~
    # PRIVATE METHODS
    # ~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _validate_sit_submission(
        cls, submission_id: int
    ) -> Optional[SimpleInteractiveToolSubmission]:
        """
        Validates the given SIT submission and checks if it should count towards a milestone.

        Returns True if any milestones should be updated, False if not.
        Returns the SimpleInteractiveToolSubmission if any milestones should be updated, None if not.
        """
        if not submission_id:
            return None

        try:
            submission = SimpleInteractiveToolSubmission.objects.get(id=submission_id)
        except SimpleInteractiveToolSubmission.DoesNotExist:
            logger.error(
                f"Cannot track event for SIT submission {submission_id} as submission does not exist."
            )
            return None

        if submission.status != SimpleInteractiveToolSubmissionStatus.COMPLETE.name:
            logger.warning(
                "MilestoneMonitor: Ignoring SIT submission as it's not COMPLETED."
            )
            return None

        if not submission.simple_interactive_tool:
            logger.error(
                "MilestoneMonitor: SimpleInteractiveToolSubmission did not have "
                "an assessment associated with it."
            )
            return None

        return submission

    @classmethod
    def _validate_answer_submission(
        cls,
        submission_id: int,
        previous_answer_status: str = "",
    ) -> Optional[SubmittedAnswer]:
        """
        Validates the given anser submission and checks if it should count towards a milestone.

        Returns the AnswerSubmission if any milestones should be updated, None if not.
        """
        if not submission_id:
            return None

        try:
            submission = SubmittedAnswer.objects.get(id=submission_id)
        except SubmittedAnswer.DoesNotExist:
            logger.error(
                f"Cannot track event for SubmittedAnswer {submission_id} as submission does not exist."
            )
            return None

        if previous_answer_status in ANSWER_STATUS_FINISHED:
            # Nothing to do here. Student already answered question, so
            # we don't need to increment any milestone
            return None

        if submission.status not in ANSWER_STATUS_FINISHED:
            # Nothing to do here. Answer isn't worthy of milestone step
            return None

        if not submission.assessment:
            logger.error(
                "MilestoneMonitor: SubmittedAnswer did not have an assessment associated with it."
            )
            return None

        return submission

    @classmethod
    def _award_course_passed_if_course_passed(cls, course: Course, student) -> bool:
        """
        Checks to see whether all milestones required by course
        are complete. If so, user has 'passed' the course and is
        given a CoursePassed entry in the database.

        A certificate and/or badge is awarded if this course is configured to award them.

        NOTE :  This method will return False if user has already passed course,
                as the True flag is supposed to signify a CoursePassed was created.

        Args:
            course:
            student:

        Returns:
            Boolean flag, True if student is given a CoursePassed

        """
        assert course is not None
        assert student is not None

        course_passed = CoursePassed.objects.filter(
            course=course, student=student
        ).first()
        if course_passed:
            # Already passed!
            return False

        required_milestones = course.milestones.filter(required_to_pass=True).all()

        # Check all required milestones. If even one hasn't been achieved,
        # student hasn't yet passed course.
        try:
            required_milestone_ids = [milestone.id for milestone in required_milestones]
            num_required = len(required_milestone_ids)
            num_achieved: int = MilestoneProgress.objects.filter(
                student=student, milestone__in=required_milestone_ids, achieved=True
            ).count()
            if num_achieved < num_required:
                return False
        except Exception:
            logger.exception("Couldn't check all milestones. Cannot complete grading")
            return False

        # Student has completed all required milestones
        course_passed_service.student_passed_course(student=student, course=course)

        return True
