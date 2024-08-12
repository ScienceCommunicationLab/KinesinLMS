import logging
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils.timezone import now

from kinesinlms.assessments.tests.factories import LongFormAssessmentFactory, SubmittedAnswerFactory
from kinesinlms.assessments.models import Assessment, SubmittedAnswer
from kinesinlms.course.constants import MilestoneType
from kinesinlms.course.exceptions import CourseFinishedException
from kinesinlms.course.models import CoursePassed, Milestone, MilestoneProgress
from kinesinlms.course.milestone_monitor import MilestoneMonitor
from kinesinlms.course.tests.factories import BlockFactory, CourseFactory
from kinesinlms.learning_library.constants import AnswerStatus, BlockType
from kinesinlms.learning_library.models import Block, UnitBlock
from kinesinlms.sits.constants import SimpleInteractiveToolSubmissionStatus
from kinesinlms.sits.models import SimpleInteractiveTool, SimpleInteractiveToolSubmission
from kinesinlms.users.tests.factories import UserFactory


logger = logging.getLogger(__name__)


class TestMilestoneMonitorTrackInteraction(TestCase):
    """
    Tests MilestoneMonitor.track_interaction* methods.
    """

    def setUp(self):
        super().setUp()
        course = CourseFactory()
        no_enrollment_user = UserFactory(username="no-enrollment-user",
                                         email="no-enrollment-user@example.com")
        enrolled_user = UserFactory(username="enrolled-user",
                                    email="enrolled-user@example.com")
        self.course = course
        self.enrolled_user = enrolled_user
        self.no_enrollment_user = no_enrollment_user

        assessment_unit_block = UnitBlock.objects.filter(
            course_unit__course=self.course,
            block__type=BlockType.ASSESSMENT.name,
            block_order=3,
        ).first()
        self.assessment_block = assessment_unit_block.block
        self.assessment = Assessment.objects.get(
            block=self.assessment_block,
        )

        sit_unit_block = UnitBlock.objects.filter(
            course_unit__course=self.course,
            block__type=BlockType.SIMPLE_INTERACTIVE_TOOL.name,
            block_order=4,
        ).first()
        self.sit_block = sit_unit_block.block
        self.sit = SimpleInteractiveTool.objects.get(
            block=self.sit_block,
        )

        # mock the calls to external tracking API
        self.patcher = patch('kinesinlms.tracking.tracker.Tracker.track')
        self.track = self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_milestone_monitor_does_not_track_assessment_events_after_course_is_finishe(self):
        self.client.force_login(self.enrolled_user)
        self.course.end_date = now() - timedelta(days=1)

        assert not MilestoneMonitor.track_interaction_by_id(
                course_id=self.course.id,
                user_id=self.enrolled_user.id,
                block_uuid=self.assessment_block.uuid,
            )

        with self.assertRaises(CourseFinishedException):
            MilestoneMonitor.track_interaction(
                course=self.course,
                student=self.enrolled_user,
                block=self.assessment_block,
            )

    def test_track_interaction_count_requirement_achieved(self):
        answer = SubmittedAnswer.objects.create(
            course=self.course,
            assessment=self.assessment,
            student=self.enrolled_user,
            status=AnswerStatus.COMPLETE.name,
        )
        milestone_achieved = MilestoneMonitor.track_interaction(
            course=self.course,
            student=self.enrolled_user,
            block=self.assessment_block,
            submission_id=answer.id,
            previous_answer_status=AnswerStatus.INCOMPLETE.name,
        )
        assert milestone_achieved

        course_passed = CoursePassed.objects.filter(
            course=self.course,
            student=self.enrolled_user,
        ).first()
        assert course_passed

    def test_track_interaction_assessment_count_graded_only_achieved(self):
        milestone = Milestone.objects.get(
            course=self.course,
        )
        milestone.count_graded_only = True
        milestone.save()
        self.assessment_block.graded = True
        self.assessment_block.save()

        answer = SubmittedAnswer.objects.create(
            course=self.course,
            assessment=self.assessment,
            student=self.enrolled_user,
            status=AnswerStatus.COMPLETE.name,
        )

        milestone_achieved = MilestoneMonitor.track_interaction(
            course=self.course,
            student=self.enrolled_user,
            block=self.assessment_block,
            submission_id=answer.id,
            previous_answer_status=AnswerStatus.INCOMPLETE.name,
        )
        assert milestone_achieved

        course_passed = CoursePassed.objects.filter(
            course=self.course,
            student=self.enrolled_user,
        ).first()
        assert course_passed

    def test_track_interaction_assessment_count_graded_only_not_achieved(self):
        milestone = Milestone.objects.get(
            course=self.course,
        )
        milestone.count_graded_only = True
        milestone.save()
        self.assessment.graded = False
        self.assessment.save()

        answer = SubmittedAnswer.objects.create(
            course=self.course,
            assessment=self.assessment,
            student=self.enrolled_user,
            status=AnswerStatus.COMPLETE.name,
        )

        milestone_achieved = MilestoneMonitor.track_interaction(
            course=self.course,
            student=self.enrolled_user,
            block=self.assessment_block,
            submission_id=answer.id,
            previous_answer_status=AnswerStatus.INCOMPLETE.name,
        )
        assert not milestone_achieved

        course_passed = CoursePassed.objects.filter(
            course=self.course,
            student=self.enrolled_user,
        ).first()
        assert not course_passed

    def test_track_interaction_assessment_min_score_achieved(self):
        milestone = Milestone.objects.get(
            course=self.course,
        )
        milestone.count_requirement = 0
        milestone.min_score_requirement = 3
        milestone.save()

        answer = SubmittedAnswer.objects.create(
            course=self.course,
            assessment=self.assessment,
            student=self.enrolled_user,
            status=AnswerStatus.COMPLETE.name,
            score=3,
        )

        milestone_achieved = MilestoneMonitor.track_interaction(
            course=self.course,
            student=self.enrolled_user,
            block=self.assessment_block,
            submission_id=answer.id,
            previous_answer_status=AnswerStatus.INCOMPLETE.name,
        )
        assert milestone_achieved

        course_passed = CoursePassed.objects.filter(
            course=self.course,
            student=self.enrolled_user,
        ).first()
        assert course_passed

    def test_track_interaction_assessment_twice(self):
        milestone = Milestone.objects.get(
            course=self.course,
        )
        milestone.count_requirement = 0
        milestone.min_score_requirement = 3
        milestone.save()

        answer = SubmittedAnswer.objects.create(
            course=self.course,
            assessment=self.assessment,
            student=self.enrolled_user,
            status=AnswerStatus.COMPLETE.name,
            score=2,
        )

        milestone_achieved = MilestoneMonitor.track_interaction(
            course=self.course,
            student=self.enrolled_user,
            block=self.assessment_block,
            submission_id=answer.id,
            previous_answer_status=AnswerStatus.INCOMPLETE.name,
        )
        assert not milestone_achieved

        # Track interaction again -- should not re-add the block.
        milestone_achieved = MilestoneMonitor.track_interaction(
            course=self.course,
            student=self.enrolled_user,
            block=self.assessment_block,
            submission_id=answer.id,
            previous_answer_status=AnswerStatus.INCOMPLETE.name,
        )
        assert not milestone_achieved

    def test_track_interaction_assessment_min_score_not_achieved(self):
        milestone = Milestone.objects.get(
            course=self.course,
        )
        milestone.count_requirement = 0
        milestone.min_score_requirement = 3
        milestone.save()

        answer = SubmittedAnswer.objects.create(
            course=self.course,
            assessment=self.assessment,
            student=self.enrolled_user,
            status=AnswerStatus.COMPLETE.name,
            score=2,
        )

        milestone_achieved = MilestoneMonitor.track_interaction(
            course=self.course,
            student=self.enrolled_user,
            block=self.assessment_block,
            submission_id=answer.id,
            previous_answer_status=AnswerStatus.INCOMPLETE.name,
        )
        assert not milestone_achieved

        course_passed = CoursePassed.objects.filter(
            course=self.course,
            student=self.enrolled_user,
        ).first()
        assert not course_passed

    def test_track_interaction_sit_min_score_achieved(self):
        milestone = Milestone.objects.get(
            course=self.course,
        )
        milestone.type = MilestoneType.SIMPLE_INTERACTIVE_TOOL_INTERACTIONS.name
        milestone.count_requirement = 0
        milestone.min_score_requirement = 3
        milestone.save()

        answer = SimpleInteractiveToolSubmission.objects.create(
            course=self.course,
            simple_interactive_tool=self.sit,
            student=self.enrolled_user,
            status=SimpleInteractiveToolSubmissionStatus.COMPLETE.name,
            score=3,
        )

        milestone_achieved = MilestoneMonitor.track_interaction(
            course=self.course,
            student=self.enrolled_user,
            block=self.sit_block,
            submission_id=answer.id,
        )
        assert milestone_achieved

        course_passed = CoursePassed.objects.filter(
            course=self.course,
            student=self.enrolled_user,
        ).first()
        assert course_passed

    def test_track_interaction_sit_min_score_not_achieved(self):
        milestone = Milestone.objects.get(
            course=self.course,
        )
        milestone.type = MilestoneType.SIMPLE_INTERACTIVE_TOOL_INTERACTIONS.name
        milestone.count_requirement = 0
        milestone.min_score_requirement = 3
        milestone.save()

        answer = SimpleInteractiveToolSubmission.objects.create(
            course=self.course,
            simple_interactive_tool=self.sit,
            student=self.enrolled_user,
            status=SimpleInteractiveToolSubmissionStatus.COMPLETE.name,
            score=2,
        )

        milestone_achieved = MilestoneMonitor.track_interaction(
            course=self.course,
            student=self.enrolled_user,
            block=self.sit_block,
            submission_id=answer.id,
        )
        assert not milestone_achieved

        course_passed = CoursePassed.objects.filter(
            course=self.course,
            student=self.enrolled_user,
        ).first()
        assert not course_passed

    def test_track_interaction_no_course_raises_exception(self):
        with self.assertRaises(ValueError):
            MilestoneMonitor.track_interaction(
                course=None, # noqa
                student=self.enrolled_user,
                block=self.assessment_block,
            )

    def test_track_interaction_no_user_raises_exception(self):
        with self.assertRaises(ValueError):
            MilestoneMonitor.track_interaction(
                course=self.course,
                student=None, # noqa
                block=self.assessment_block, # noqa
            )

    def test_track_interaction_no_block_raises_exception(self):
        with self.assertRaises(ValueError):
            MilestoneMonitor.track_interaction(
                course=self.course,
                student=self.enrolled_user,
                block=None,  # noqa
            )

    def test_track_interaction_no_answer_submission(self):
        assert MilestoneMonitor.track_interaction_by_id(
            course_id=self.course.id,
            user_id=self.enrolled_user.id,
            block_uuid=self.assessment_block.uuid,
            submission_id=1000,
        )
        assert not MilestoneMonitor.track_interaction(
            course=self.course,
            student=self.enrolled_user,
            block=self.assessment_block,
            submission_id=1000,
        )

    def test_track_interaction_no_sit_milestones(self):
        answer = SimpleInteractiveToolSubmission.objects.create(
            course=self.course,
            simple_interactive_tool=self.sit,
            student=self.enrolled_user,
            status=SimpleInteractiveToolSubmissionStatus.COMPLETE.name,
            score=3,
        )

        assert MilestoneMonitor.track_interaction_by_id(
            course_id=self.course.id,
            user_id=self.enrolled_user.id,
            block_uuid=self.sit_block.uuid,
            submission_id=answer.id,
        )
        assert not MilestoneMonitor.track_interaction(
            course=self.course,
            student=self.enrolled_user,
            block=self.sit_block,
            submission_id=answer.id,
        )

    def test_track_interaction_no_sit_submission(self):
        milestone = Milestone.objects.get(
            course=self.course,
        )
        milestone.type = MilestoneType.SIMPLE_INTERACTIVE_TOOL_INTERACTIONS.name
        milestone.save()
        assert MilestoneMonitor.track_interaction_by_id(
            course_id=self.course.id,
            user_id=self.enrolled_user.id,
            block_uuid=self.sit_block.uuid,
            submission_id=1000,
        )
        assert not MilestoneMonitor.track_interaction(
            course=self.course,
            student=self.enrolled_user,
            block=self.sit_block,
            submission_id=1000,
        )


class TestMilestoneMonitorAssessmentMixin:
    """
    Common data shared between MilestoneMonitor Assessment tests.
    """
    def setUp(self):
        super().setUp() # noqa

        self.course = CourseFactory()
        self.block1 = BlockFactory(type=BlockType.ASSESSMENT.name)
        self.block2 = BlockFactory(type=BlockType.ASSESSMENT.name)
        self.assessment1 = LongFormAssessmentFactory(block=self.block1, max_score=2)
        self.assessment2 = LongFormAssessmentFactory(block=self.block2, max_score=3)

        self.setup_milestones()

        self.student1 = UserFactory()
        self.student2 = UserFactory()

        # Student1 submits answers to both assessments, and so will achieve the milestone.
        self.answer1 = SubmittedAnswerFactory(
            course=self.course,
            assessment=self.assessment1,
            student=self.student1,
            score=self.assessment1.max_score,
        )
        assert not MilestoneMonitor.track_interaction(
            course=self.course,
            student=self.student1,
            block=self.block1,
            submission_id=self.answer1.id,
        )
        self.answer2 = SubmittedAnswerFactory(
            course=self.course,
            assessment=self.assessment2,
            student=self.student1,
            score=self.assessment2.max_score,
        )
        MilestoneMonitor.track_interaction(
            course=self.course,
            student=self.student1,
            block=self.block2,
            submission_id=self.answer2.id,
        )
        self.progress1 = MilestoneProgress.objects.get(course=self.course, student=self.student1)

        # Student2 submits an answer to one assessment, and so has not achieved the milestone.
        self.answer3 = SubmittedAnswerFactory(
            course=self.course,
            assessment=self.assessment2,
            student=self.student2,
            score=self.assessment2.max_score,
        )
        MilestoneMonitor.track_interaction(
            course=self.course,
            student=self.student2,
            block=self.block2,
            submission_id=self.answer3.id,
            previous_answer_status=AnswerStatus.INCOMPLETE.name,
        )
        self.progress2 = MilestoneProgress.objects.get(course=self.course, student=self.student2)

    def setup_milestones(self):
        """
        Subclasses should use this method to update the course milestone(s)
        prior to tracking interactions.
        """
        pass

    def check_progress(self, progress: MilestoneProgress, total_score, count=1, achieved=False):
        """
        Checks the updated total_score for both our MilestoneProgress objects.
        """
        if total_score is None:
            with self.assertRaises(MilestoneProgress.DoesNotExist):
                progress.refresh_from_db()
        else:
            progress.refresh_from_db()

            assert progress.achieved == achieved
            assert progress.count == count
            assert progress.total_score == total_score


class TestMilestoneMonitorRemoveAssessment(TestMilestoneMonitorAssessmentMixin, TestCase):
    """
    Tests MilestoneMonitor.remove_assessment_from_progress* methods.
    """
    def setUp(self):
        super().setUp()

        # Check that baseline MilestoneProgress objects are as expected
        self.check_progress(self.progress1, total_score=5, count=2, achieved=True)
        self.check_progress(self.progress2, total_score=3, count=1, achieved=False)

    def setup_milestones(self):
        """
        Modify the factory-generated Milestone to require 2 assessments to pass.
        """
        super().setup_milestones()

        milestone = self.course.milestones.first()
        milestone.count_requirement = 2
        milestone.save()

    def test_remove_assessment_from_progress_for_course(self):
        """
        Removing all assessments from a course's MilestoneProgress will delete
        all assessment-related MilestoneProgress objects.
        """
        with self.assertNumQueries(4):
            count = MilestoneMonitor.remove_assessment_from_progress_by_id(course_id=self.course.id)

        # Both MilestoneProgress objects were removed
        assert count == 2
        self.check_progress(self.progress1, total_score=None)
        self.check_progress(self.progress2, total_score=None)

    def test_remove_assessment_from_progress_for_student(self):
        """
        Removing a user's assessments from a course's MilestoneProgress
        will delete any assessment-related MilestoneProgress objects for that user.
        """
        with self.assertNumQueries(5):
            count = MilestoneMonitor.remove_assessment_from_progress_by_id(course_id=self.course.id,
                                                                           user_id=self.student2.id)
        # student1's progress is unchanged, but student2's has been removed.
        assert count == 1
        self.check_progress(self.progress1, total_score=5, count=2, achieved=True)
        self.check_progress(self.progress2, total_score=None)

    def test_remove_assessment_from_progress_for_assessment(self):
        """
        Removing one assessment from a course's MilestoneProgress will update
        all assessment-related MilestoneProgress objects.
        """
        with self.assertNumQueries(6):
            count = MilestoneMonitor.remove_assessment_from_progress_by_id(course_id=self.course.id,
                                                                           assessment_id=self.assessment2.id)
        assert count == 2
        self.check_progress(self.progress1, total_score=2, count=1, achieved=True)
        self.check_progress(self.progress2, total_score=0, count=0, achieved=False)

    def test_remove_assessment_from_progress_for_student_assessment(self):
        """
        Removing one user's one assessment from a course's MilestoneProgress will update
        that user's assessment-related MilestoneProgress object.
        """
        with self.assertNumQueries(7):
            count = MilestoneMonitor.remove_assessment_from_progress_by_id(course_id=self.course.id,
                                                                           user_id=self.student1.id,
                                                                           assessment_id=self.assessment2.id)
        assert count == 1
        self.check_progress(self.progress1, total_score=2, count=1, achieved=True)
        self.check_progress(self.progress2, total_score=3, count=1, achieved=False)

        # Running the same delete again should do nothing to the existing MilestoneProgress.
        with self.assertNumQueries(6):
            count2 = MilestoneMonitor.remove_assessment_from_progress_by_id(course_id=self.course.id,
                                                                            user_id=self.student1.id,
                                                                            assessment_id=self.assessment2.id)
        assert count2 == 0
        self.check_progress(self.progress1, total_score=2, count=1, achieved=True)
        self.check_progress(self.progress2, total_score=3, count=1, achieved=False)

    def test_remove_assessment_from_progress_bad_course(self):
        with self.assertNumQueries(1):
            count = MilestoneMonitor.remove_assessment_from_progress_by_id(course_id=124567)
        assert count == 0

    def test_remove_assessment_from_progress_course_finished(self):
        self.course.end_date = now() - timedelta(days=1)
        self.course.save()
        with self.assertNumQueries(1):
            count = MilestoneMonitor.remove_assessment_from_progress_by_id(course_id=self.course.id)
        assert count == 0

    def test_remove_assessment_from_progress_course_no_milestones(self):
        milestone = self.course.milestones.first()
        milestone.type = MilestoneType.VIDEO_PLAYS.name
        milestone.save()
        with self.assertNumQueries(2):
            count = MilestoneMonitor.remove_assessment_from_progress_by_id(course_id=self.course.id)
        assert count == 0

    def test_remove_assessment_from_progress_bad_student(self):
        with self.assertNumQueries(2):
            count = MilestoneMonitor.remove_assessment_from_progress_by_id(course_id=self.course.id,
                                                                           user_id=124345)
        assert count == 0

    def test_remove_assessment_from_progress_bad_assessment(self):
        with self.assertNumQueries(3):
            count = MilestoneMonitor.remove_assessment_from_progress_by_id(course_id=self.course.id,
                                                                           user_id=self.student1.id,
                                                                           assessment_id=124345)
        assert count == 0


class TestMilestoneMonitorRescoreAssessment(TestMilestoneMonitorAssessmentMixin, TestCase):
    """
    Tests MilestoneMonitor.rescore_assessment_progress*
    """

    def setUp(self):
        super().setUp()

        # Check that baseline MilestoneProgress objects are as expected
        self.check_progress(self.progress1, total_score=5, count=2)
        self.check_progress(self.progress2, total_score=3, count=1)

    def setup_milestones(self):
        """
        Modify the factory-generated Milestone to require a total score of 9 to pass.
        """
        super().setup_milestones()

        milestone = self.course.milestones.first()
        milestone.count_requirement = 0
        milestone.min_score_requirement = 9
        milestone.save()

    @patch("kinesinlms.course.milestone_monitor.MilestoneMonitor._award_course_passed_if_course_passed")
    def test_rescore_assessment_progress_for_course_with_completion(self, mock_course_passed):
        # Modify the assessment max_scores so that rescoring will trigger course completion for student1.
        self.assessment1.max_score = 4
        self.assessment1.save()
        self.assessment2.max_score = 5
        self.assessment2.save()

        with self.assertNumQueries(13):
            count = MilestoneMonitor.rescore_assessment_progress_by_id(course_id=self.course.id)
        assert count == 2

        mock_course_passed.assert_called_once_with(student=self.student1, course=self.course)

        # Both MilestoneProgress objects were updated, and progress1 was achieved.
        self.check_progress(self.progress1, total_score=9, count=2, achieved=True)
        self.check_progress(self.progress2, total_score=5, count=1)

    def test_rescore_assessment_progress_for_course_no_completion(self):
        # Modify the assessment max_scores so that rescoring will have an effect on total_score,
        # but won't trigger course completion.
        self.assessment1.max_score = 3
        self.assessment1.save()
        self.assessment2.max_score = 4
        self.assessment2.save()

        with self.assertNumQueries(13):
            count = MilestoneMonitor.rescore_assessment_progress_by_id(course_id=self.course.id)
        assert count == 2

        # Both MilestoneProgress objects were updated
        self.check_progress(self.progress1, total_score=7, count=2)
        self.check_progress(self.progress2, total_score=4, count=1)

    def test_rescore_assessment_progress_for_course_count_graded_only(self):
        # Make the milestone count graded assessments only...
        milestone = self.course.milestones.first()
        milestone.count_graded_only = True
        milestone.save()

        # ...and make the assessments "ungraded", so none will count against the milestone.
        self.assessment1.graded = False
        self.assessment1.save()
        self.assessment2.graded = False
        self.assessment2.save()

        with self.assertNumQueries(8):
            count = MilestoneMonitor.rescore_assessment_progress_by_id(course_id=self.course.id)
        assert count == 2

        # Both MilestoneProgress objects were updated -- all blocks removed.
        self.check_progress(self.progress1, total_score=0, count=0)
        self.check_progress(self.progress2, total_score=0, count=0)

    def test_rescore_assessment_progress_for_student(self):
        # Modify the assessment max_scores so that rescoring will have an effect on total_score
        self.assessment1.max_score = 4
        self.assessment1.save()
        self.assessment2.max_score = 5
        self.assessment2.save()

        with self.assertNumQueries(8):
            count = MilestoneMonitor.rescore_assessment_progress_by_id(course_id=self.course.id,
                                                                       user_id=self.student2.id)
        assert count == 1

        # Only student2's MilestoneProgress objects should be updated
        self.check_progress(self.progress1, total_score=5, count=2)
        self.check_progress(self.progress2, total_score=5, count=1)

    def test_rescore_assessment_progress_for_assessment(self):
        # Update scores on both assessments
        self.assessment1.max_score = 4
        self.assessment1.save()
        self.assessment2.max_score = 4
        self.assessment2.save()

        # ...but only rescore assessment2.
        with self.assertNumQueries(13):
            count = MilestoneMonitor.rescore_assessment_progress_by_id(course_id=self.course.id,
                                                                       assessment_id=self.assessment2.id)
        assert count == 2

        # The updated scores reflect the original assessment1.max_score and the updated assessment2.max_score
        self.check_progress(self.progress1, total_score=6, count=2)
        self.check_progress(self.progress2, total_score=4, count=1)

    def test_rescore_assessment_progress_for_student_assessment(self):
        self.assessment1.max_score = 5
        self.assessment1.save()
        self.assessment2.max_score = 4
        self.assessment2.save()

        with self.assertNumQueries(9):
            count = MilestoneMonitor.rescore_assessment_progress_by_id(course_id=self.course.id,
                                                                       user_id=self.student2.id,
                                                                       assessment_id=self.assessment2.id)
        assert count == 1

        # Only student2's MilestoneProgress object was updated
        self.check_progress(self.progress1, total_score=5, count=2)
        self.check_progress(self.progress2, total_score=4, count=1)

    def test_rescore_assessment_progress_for_no_matching_records(self):
        self.assessment1.max_score = 5
        self.assessment1.save()
        self.assessment2.max_score = 4
        self.assessment2.save()

        # student2 has no submissions for assessment1, so this should be a no-op.
        with self.assertNumQueries(4):
            count = MilestoneMonitor.rescore_assessment_progress_by_id(course_id=self.course.id,
                                                                       user_id=self.student2.id,
                                                                       assessment_id=self.assessment1.id)
        assert count == 0

        # No MilestoneProgress objects were updated
        self.check_progress(self.progress1, total_score=5, count=2)
        self.check_progress(self.progress2, total_score=3, count=1)

    def test_rescore_assessment_progress_missing_progress(self):
        # Add additional answer which hasn't been recorded against progress yet.
        SubmittedAnswerFactory(
            course=self.course,
            assessment=self.assessment1,
            student=self.student2,
            score=3,
        )

        with self.assertNumQueries(15):
            count = MilestoneMonitor.rescore_assessment_progress_by_id(course_id=self.course.id)
        assert count == 2

        # student2 should have a new block.
        self.check_progress(self.progress1, total_score=5, count=2)
        self.check_progress(self.progress2, total_score=5, count=2)

    def test_rescore_assessment_progress_bad_course(self):
        with self.assertNumQueries(1):
            count = MilestoneMonitor.rescore_assessment_progress_by_id(course_id=124567)
        assert count == 0

    def test_rescore_assessment_progress_course_finished(self):
        self.course.end_date = now() - timedelta(days=1)
        self.course.save()
        with self.assertNumQueries(1):
            count = MilestoneMonitor.rescore_assessment_progress_by_id(course_id=self.course.id)
        assert count == 0

    def test_rescore_assessment_progress_course_no_milestones(self):
        milestone = self.course.milestones.first()
        milestone.type = MilestoneType.VIDEO_PLAYS.name
        milestone.save()
        with self.assertNumQueries(2):
            count = MilestoneMonitor.rescore_assessment_progress_by_id(course_id=self.course.id)
        assert count == 0

    def test_rescore_assessment_progress_bad_student(self):
        with self.assertNumQueries(2):
            count = MilestoneMonitor.rescore_assessment_progress_by_id(course_id=self.course.id,
                                                                       user_id=124345)
        assert count == 0

    def test_rescore_assessment_progress_bad_assessment(self):
        with self.assertNumQueries(3):
            count = MilestoneMonitor.rescore_assessment_progress_by_id(course_id=self.course.id,
                                                                       user_id=self.student1.id,
                                                                       assessment_id=124345)
        assert count == 0
